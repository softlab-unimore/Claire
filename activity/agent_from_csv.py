import os
import pandas as pd
import io

from .methods import OpenAIModel
from .prompts.prompts_csv.phase import phase_prompt
from .prompts.prompts_csv.criteria import criteria_prompt
from .prompts.prompts_csv.interaction import interaction_prompt
from .models import Dataset

from functools import lru_cache
from copy import deepcopy
from django.shortcuts import get_object_or_404

class AgentFromCsv:
    def __init__(self):
        attr = {
            "model_name": os.environ["OPENAI_MODEL_NAME"],
            "temperature": float(os.environ["OPENAI_TEMPERATURE"]),
        }
        self.model = OpenAIModel(**attr)
        self.num_stages = None

        #self.max_num_interactions = 3 # TODO: this will likely need to be set by the user (e.g. from csv) in the future

    def is_activity_finished(self, current_phase, activity):
        phases_df, _, _, _ = self.load_df(activity)
        if current_phase > len(phases_df):
            return True
        return False

    def are_interactions_too_many(self, activity, current_phase, num_interactions):
        phases_df, _, _, _ = self.load_df(activity)
        max_num_interactions = phases_df[phases_df["Fase"] == current_phase]["Numero interazioni massimo"].iloc[0]

        if num_interactions >= max_num_interactions:
            return True
        return False

    @lru_cache()
    def load_df(self, activity):
        dataset = activity.dataset
        try:
            phases = pd.read_excel(io.BytesIO(dataset.phases))
            criteria = pd.read_excel(io.BytesIO(dataset.criteria))
            interaction = pd.read_excel(io.BytesIO(dataset.interaction))
            logic = pd.read_excel(io.BytesIO(dataset.logic))
        except:
            phases = pd.read_csv(io.BytesIO(dataset.phases))
            criteria = pd.read_csv(io.BytesIO(dataset.criteria))
            interaction = pd.read_csv(io.BytesIO(dataset.interaction))
            logic = pd.read_csv(io.BytesIO(dataset.logic))

        self.num_stages = len(phases)
        return phases, criteria, interaction, logic

    def apply_phase(self, current_phase, messages, total_messages, activity, streaming=False):
        phases_df, _, _, _ = self.load_df(activity)
        phase_row = phases_df[phases_df["Fase"] == current_phase]
        assert len(phase_row) == 1
        phase_row = phase_row.iloc[0,:]
        attr = {
            "phase_number": phase_row["Fase"],
            "phase_name": phase_row["Nome"],
            "phase_goal": phase_row["Obiettivo"],
            "phase_description": phase_row["Descrizione"],
        }
        prompt = phase_prompt.format(**attr)
        messages.append({
            "text": prompt,
            "sender": "system"
        })
        total_messages.append({
            "text": prompt,
            "sender": "system"
        })
        prompt = "\n".join([message["text"]+"\n" for message in messages])
        messages = messages[:-1]
        if messages[-1]["sender"] == "system":
            messages = messages[:-1]

        if phase_row["Input non modificabile"] != "":
            non_modifiable_output = phase_row["Input non modificabile"]
        else:
            non_modifiable_output = None

        if not streaming:
            result = self.model.query(prompt)

            messages.append({
                "text": "BOT: "+result,
                "sender": "bot"
            })
            total_messages.append({
                "text": "BOT: "+result,
                "sender": "bot"
            })

            if non_modifiable_output is not None:
                messages.append({
                    "text": non_modifiable_output,
                    "sender": "system"
                })
                total_messages.append({
                    "text": non_modifiable_output,
                    "sender": "system"
                })

            return messages, total_messages, non_modifiable_output

        acc = []

        def token_gen():
            # IMPORTANT: you need a streaming iterator from your model
            # e.g. self.model.query(prompt, stream=True) or self.model.query_stream(prompt)
            for chunk in self.model.call_gpt_stream(prompt):
                # chunk should be a string token/partial
                if not chunk:
                    continue
                acc.append(chunk)
                yield chunk

        def finalize(non_modifiable_output=non_modifiable_output):
            result = "".join(acc)
            bot_text = "BOT: " + result
            messages.append({"text": bot_text, "sender": "bot"})
            total_messages.append({"text": bot_text, "sender": "bot"})

            if non_modifiable_output is not None:
                messages.append({"text": non_modifiable_output, "sender": "system"})
                total_messages.append({"text": non_modifiable_output, "sender": "system"})

            return messages, total_messages

        return token_gen(), finalize, non_modifiable_output

    def apply_criteria(self, current_phase, messages, total_messages, activity, suitability_counter):
        _, criteria_df, _, _ = self.load_df(activity)
        suitability = True
        rows_criteria = criteria_df[criteria_df["Fase"] == current_phase]
        results = []
        for i, row in rows_criteria.iterrows():
            l_descriptions = ""
            for col_number in range(0, (len(criteria_df.columns)-2)//2):
                num = col_number + 1
                l_descriptions += f"L{num}) "
                l_descriptions += row[f"L{num}-titolo"]+": "
                l_descriptions += row[f"L{num}-descrizione"]+"\n"

            attr = {
                "phase_number": row["Fase"],
                "criteria_name": row["Nome"],
                "l_descriptions": l_descriptions,
            }
            prompt = criteria_prompt.format(**attr)
            messages.append({
                "text": prompt,
                "sender": "system"
            })
            total_messages.append({
                "text": prompt,
                "sender": "system"
            })

            prompt = "\n".join([message["text"]+"\n" for message in messages])
            print(prompt)
            result = self.model.query(prompt)
            total_messages.append({
                "text": result,
                "sender": "system"
            })
            print(result)
            explanation = result
            result = self.model.extract_result(result, "risposta finale:")
            results.append(result)
            messages = messages[:-1]
            print(f"Livello del criterio: {result}")
            if result.strip().lower() == "non inerente":
                suitability = False
                break

        """messages.append({
            "text": results[0],
            "sender": "bot"
        })"""
        if suitability_counter >= 3:
            suitability = True

        return messages, total_messages, results[0], suitability, explanation # currently, the method works only with one criteria for each phase

    def apply_interaction(self, current_phase, messages, total_messages, interaction_name, activity, end=False, streaming=False, skip=False):
        _, _, interaction_df, _ = self.load_df(activity)

        if interaction_name == "next" and not end:
            messages.append({
                "text": "Devo rispondere che ho compreso ciò che ha detto, per poi procedere con l'interazione successiva.",
                "sender": "system"
            })
            total_messages.append({
                "text": "Devo rispondere che ho compreso ciò che ha detto, per poi procedere con l'interazione successiva.",
                "sender": "system"
            })
            return messages, total_messages, -1
        elif interaction_name == "next":
            messages.append({
                "text": "Devo rispondere che ho compreso ciò che ha detto, per poi concludere l'attività dicendo qualcosa di simile a \"Congratulazioni, hai terminato l'attività!\".",
                "sender": "system"
            })
            total_messages.append({
                "text": "Devo rispondere che ho compreso ciò che ha detto, per poi concludere l'attività dicendo qualcosa di simile a \"Congratulazioni, hai terminato l'attività!\".",
                "sender": "system"
            })
        else:
            rows_interaction = interaction_df[(interaction_df["Fase"] == current_phase) & (interaction_df["Nome"] == interaction_name)][:1] # this case needs to be dealt on loading of the .csv files
            assert len(rows_interaction) == 1
            rows_interaction = rows_interaction.iloc[0,:]
            attr = {
                "interaction_name": interaction_name,
                "interaction_description": rows_interaction["Descrizione"],
            }
            prompt = interaction_prompt.format(**attr)
            if end:
                prompt += "\nAlla fine, devi finire il tuo messaggio concludendo l'attività. Devi concludere l'attività dicendo qualcosa di simile a \"Congratulazioni, hai terminato l'attività!\"."
            messages.append({
                "text": prompt,
                "sender": "system"
            })
            total_messages.append({
                "text": prompt,
                "sender": "system"
            })

        prompt = "\n".join([message["text"] + "\n" for message in messages])
        if not skip:
            messages = messages[:-1]
        else:
            return messages, total_messages, interaction_name

        if not streaming:
            result = self.model.query(prompt)
            messages.append({
                "text": "BOT: "+result,
                "sender": "bot"
            })
            total_messages.append({
                "text": "BOT: "+result,
                "sender": "bot"
            })

            print(f"Interazione corrente: {interaction_name}")

            return messages, total_messages, interaction_name

        acc = []

        def token_gen():
            # IMPORTANT: you need a streaming iterator from your model
            # e.g. self.model.query(prompt, stream=True) or self.model.query_stream(prompt)
            for chunk in self.model.call_gpt_stream(prompt):
                # chunk should be a string token/partial
                if not chunk:
                    continue
                acc.append(chunk)
                yield chunk

        def finalize():
            result = "".join(acc)
            bot_text = "BOT: " + result
            messages.append({"text": bot_text, "sender": "bot"})
            total_messages.append({"text": bot_text, "sender": "bot"})

            return messages, total_messages

        return token_gen(), finalize, interaction_name

    def apply_logic(self, current_phase, evaluation, activity, old_interaction_name=None):
        _, _, _, logic_df = self.load_df(activity)

        try:
            rows_logic = logic_df[(logic_df["Fase"] == current_phase) &
                                        (logic_df["Criterio"] == evaluation.upper())]

            if old_interaction_name is not None:
                rows_logic = rows_logic[rows_logic["Interazione Precedente"] == old_interaction_name]

            rows_logic = rows_logic.iloc[0, :]
        except:
            print(logic_df.head())
            print(current_phase)
            rows_logic = logic_df[(logic_df["Fase"] == current_phase)]
            rows_logic = rows_logic.iloc[0, :]

        if old_interaction_name is None:
            next_interaction_name = rows_logic["Interazione Precedente"]
        else:
            next_interaction_name = rows_logic["Interazione"]

        return next_interaction_name