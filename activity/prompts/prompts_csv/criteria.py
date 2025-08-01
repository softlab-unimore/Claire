criteria_prompt = """Dobbiamo valutare la precedente interazione del bambino.
Al momento, ci troviamo nella fase {phase_number}.
La valutazione si basa sul criterio "{criteria_name}". Il criterio viene analizzato in base ai seguenti indicatori di valutazione:

{l_descriptions}

Prima ragiona step-by-step. Infine, scrivi "Risposta finale: " seguito esclusivamente dal nome dell'indicatore di valutazione ("L1", "L2", ..., "Ln").
Non scrivere nient'altro dopo "Risposta finale: ".
"""