import os
import pandas as pd
import io
import pickle
import random

from methods import OpenAIModel
from prompts.prompts_csv.not_inherent_prompt import not_inherent_prompt
from prompts.prompts_csv.phase import phase_prompt
from prompts.prompts_csv.criteria import criteria_prompt
from prompts.prompts_csv.interaction import interaction_prompt
from prompts.prompts_csv.system_prompt import system_prompt

from functools import lru_cache
from copy import deepcopy
from django.shortcuts import get_object_or_404

from tqdm import tqdm

class AgentFromCsv:
    def __init__(self):
        attr = {
            "model_name": os.environ["OPENAI_MODEL_NAME"],
            "temperature": float(os.environ["OPENAI_TEMPERATURE"]),
        }
        self.model = OpenAIModel(**attr)
        self.num_stages = None

    def is_activity_finished(self, current_phase):
        phases_df, _, _, _ = self.load_df()
        if current_phase > len(phases_df):
            return True
        return False

    def are_interactions_too_many(self, current_phase, num_interactions, suitability_counter):
        phases_df, _, _, _ = self.load_df()
        max_num_interactions = phases_df[phases_df["Fase"] == current_phase]["Numero interazioni massimo"].iloc[0]

        if num_interactions-suitability_counter >= max_num_interactions:
            return True
        return False

    @lru_cache()
    def load_df(self):
        phases_path = "phases.xlsx"
        criteria_path = "criteria.xlsx"
        interaction_path = "interaction.xlsx"
        logic_path = "logic.xlsx"
        try:
            phases = pd.read_excel(phases_path)
            criteria = pd.read_excel(criteria_path)
            interaction = pd.read_excel(interaction_path)
            logic = pd.read_excel(logic_path)
        except:
            phases = pd.read_csv(phases_path)
            criteria = pd.read_csv(criteria_path)
            interaction = pd.read_csv(interaction_path)
            logic = pd.read_csv(logic_path)

        self.num_stages = len(phases)
        return phases, criteria, interaction, logic

    def apply_phase(self, current_phase, messages, total_messages):
        phases_df, _, _, _ = self.load_df()
        phase_row = phases_df[phases_df["Fase"] == current_phase]
        assert len(phase_row) == 1
        phase_row = phase_row.iloc[0,:]
        attr = {
            "phase_number": phase_row["Fase"],
            "phase_name": phase_row["Nome"],
            "phase_goal": phase_row["Obiettivo"],
            "phase_description": phase_row["Descrizione"],
        }
        if len(messages) == 0:
            messages.append({
                "text": system_prompt,
                "sender": "system"
            })
            total_messages.append({
                "text": system_prompt,
                "sender": "system"
            })

        prompt = phase_prompt.format(**attr)

        messages.append({
            "text": "SYSTEM: "+prompt,
            "sender": "system"
        })
        total_messages.append({
            "text": "SYSTEM: "+prompt,
            "sender": "system"
        })
        prompt = "\n".join([message["text"]+"\n" for message in messages])
        #if messages[-1]["sender"] == "system":
        #    messages = messages[:-1]

        if phase_row["Input non modificabile"] != "":
            non_modifiable_output = phase_row["Input non modificabile"]
        else:
            non_modifiable_output = None

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

    def apply_criteria(self, current_phase, messages, total_messages, suitability_counter):
        _, criteria_df, _, _ = self.load_df()
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
            messages_to_criteria = [msg for msg in messages if msg["sender"] != "system"][-3:]
            messages_to_criteria.append({
                "text": "SYSTEM: "+prompt,
                "sender": "system"
            })
            total_messages.append({
                "text": "SYSTEM: "+prompt,
                "sender": "system"
            })

            prompt = "\n".join([message["text"]+"\n" for message in messages_to_criteria])

            result = self.model.query(prompt)
            total_messages.append({
                "text": result,
                "sender": "system"
            })

            explanation = result
            result = self.model.extract_result(result, "risposta finale:")
            results.append(result)
            #messages = messages[:-1]

            if result.strip().lower() == "non inerente":
                suitability = False
                break

        """messages.append({
            "text": results[0],
            "sender": "bot"
        })"""
        if suitability_counter >= 3:
            suitability = True

        return messages, total_messages, results[0].strip().lower(), suitability, explanation # currently, the method works only with one criteria for each phase

    def apply_interaction(self, current_phase, messages, total_messages, interaction_name, criteria, end=False, skip=False):
        _, _, interaction_df, _ = self.load_df()

        if criteria == "non inerente":
            messages.append({
                "text": not_inherent_prompt,
                "sender": "system"
            })
            total_messages.append({
                "text": not_inherent_prompt,
                "sender": "system"
            })
            #return messages, total_messages, -1
        elif interaction_name == "next" and not end:
            messages.append({
                "text": "Devo rispondere che ho compreso ciò che ha detto, per poi procedere con l'interazione successiva.",
                "sender": "system"
            })
            total_messages.append({
                "text": "Devo rispondere che ho compreso ciò che ha detto, per poi procedere con l'interazione successiva.",
                "sender": "system"
            })
            #return messages, total_messages, -1
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

        result = self.model.query(prompt)
        messages.append({
            "text": "BOT: "+result,
            "sender": "bot"
        })
        total_messages.append({
            "text": "BOT: "+result,
            "sender": "bot"
        })

        return messages, total_messages, interaction_name

    def apply_logic(self, current_phase, evaluation, old_interaction_name=None):
        _, _, _, logic_df = self.load_df()

        try:
            rows_logic = logic_df[(logic_df["Fase"] == current_phase) &
                                        (logic_df["Criterio"].str.lower() == evaluation.lower())]

            if old_interaction_name is not None:
                rows_logic = rows_logic[rows_logic["Interazione Precedente"] == old_interaction_name]

            rows_logic = rows_logic.iloc[0, :]
        except:
            rows_logic = logic_df[(logic_df["Fase"] == current_phase)]
            rows_logic = rows_logic.iloc[0, :] # this always takes the first row, which could become troublesome if the first interaction of the phase is thinking aloud

        if old_interaction_name is None:
            next_interaction_name = rows_logic["Interazione Precedente"]
        else:
            next_interaction_name = rows_logic["Interazione"]

        return next_interaction_name

    def apply_llm_student_response(self, messages, total_messages, text_input=None):
        if text_input is None:
            prompt = "\n".join([message["text"] + "\n" for message in messages])
            result = self.model.query(f"{prompt}\n\nOra, come studente di scuola primaria, rispondi al bot in modo appropriato.\nStudente: ")
            messages.append({
                "text": "USER: " + result,
                "sender": "user"
            })
            total_messages.append({
                "text": "USER: " + result,
                "sender": "user"
            })
        else:
            messages.append({
                "text": "USER: " + text_input,
                "sender": "user"
            })
            total_messages.append({
                "text": "USER: " + text_input,
                "sender": "user"
            })
        return messages, total_messages

if __name__ == "__main__":
    from deep_translator import GoogleTranslator

    agent = AgentFromCsv()
    phases, criteria, interaction, logic = agent.load_df()
    final_data = []

    with open("prompts.pkl", "rb") as f:
        prompts = pickle.load(f)

    prompts = prompts[:150]
    gt = GoogleTranslator(source="en", target="it")
    translation_errors = 0
    for k, prompt in tqdm(enumerate(prompts), desc="Iterating over prompts..."):
        try:
            chunks = [prompt[x:x + 4999] for x in range(0, len(prompt), 4999)]
            prompt = gt.translate_batch(chunks)
            prompt = "".join(prompt)
        except:
            translation_errors += 1
            print("Translation error occurred. Keeping english for this prompt.")

        random_phase = random.randint(0, len(phases) - 1)
        random_interaction = random.randint(0, phases.loc[random_phase, "Numero interazioni massimo"] - 1)
        interaction_name = None
        current_phase = 1
        messages = []
        total_messages = []
        next_prompt = False

        for i in range(len(phases)):
            current_phase = i + 1
            messages, total_messages, _ = agent.apply_phase(current_phase, messages, total_messages)
            suitability_counter = 0

            for j in range(phases.loc[i, "Numero interazioni massimo"]):
                if i == random_phase and j == random_interaction:
                    messages, total_messages = agent.apply_llm_student_response(messages, total_messages, text_input=prompt)
                    next_prompt = True
                else:
                    messages, total_messages = agent.apply_llm_student_response(messages, total_messages)

                messages, total_messages, criteria, suitability, explanation = agent.apply_criteria(current_phase, messages, total_messages, suitability_counter)
                if criteria == "non inerente":
                    suitability_counter += 1
                    if interaction_name is None:
                        interaction_name = agent.apply_logic(current_phase, criteria)
                else:
                    interaction_name = agent.apply_logic(current_phase, criteria, interaction_name)
                messages, total_messages, interaction_name = agent.apply_interaction(current_phase, messages, total_messages, interaction_name, criteria)

                if next_prompt:
                    break

            if next_prompt:
                break

        """for msg in total_messages:
            print(msg["text"])
            print()
            print("*********************************************")
            print()
        print(a)"""
        final_data.append([messages, total_messages, "jailbreak"]) #"jailbreak" if k < 200 else "regular"])
        if k % 50 == 0:
            pd.DataFrame(final_data, columns=["messages", "total_messages", "prompt_type"]).to_csv("safety_results_jailbreak.csv", index=False)

    pd.DataFrame(final_data, columns=["messages", "total_messages", "prompt_type"]).to_csv("safety_results_jailbreak.csv", index=False)
    print("Translation errors:", translation_errors)
    print("Finish!")
    """print("Final messages:")
    for message in messages:
        print(f"{message['sender']}: {message['text']}")"""