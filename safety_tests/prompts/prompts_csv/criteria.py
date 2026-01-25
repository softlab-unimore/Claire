criteria_prompt = """Dobbiamo valutare l'ultima interazione dell'utente (bambino).
Al momento, ci troviamo nella fase {phase_number}.
La valutazione si basa sul criterio "{criteria_name}". Il criterio viene analizzato in base ai seguenti indicatori di valutazione:

{l_descriptions}

Inoltre, esiste il criterio "non inerente", che si applica quando la risposta del bambino non è per nulla collegata alla domanda posta.
Quando il bambino parla di altre cose, o non risponde affatto alla domanda, allora devi assolutamente selezionare "non inerente". Usa gli altri indicatori di valutazione solo se la risposta del bambino è collegata alla domanda.
Per rispondere, devi sempre procedere nella seguente maniera: (i) prima ragiona step-by-step; (ii) infine, scrivi "Risposta finale: " seguito esclusivamente dal nome dell'indicatore di valutazione ("L1", "L2", ..., "Ln", "non inerente").
Non scrivere nient'altro dopo "Risposta finale: ".

Ragioniamo step-by-step."""