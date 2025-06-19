prompt_stage1 = """
{messages}

Al momento, siamo in fase {stage}.
Dati i seguenti messaggi, dobbiamo capire se possiamo passare alla fase successiva o no.
In particolare, capiamo se nell'ultima fase:
1. I messaggi scritti dal bambino (non dal bot) sono stati almeno 3 o 4;
2. Gli scambi sono stati significativi: il bambino ha dato risposte coerenti, anche se non completamente corrette. Queste risposte significative, però, devono essere inerenti all'attività, e non coinvolgere tematiche non adatte ai bambini.

Prima scrivi dettagliatamente il tuo ragionamento. Poi, alla fine, scrivi "Risposta finale:" seguito esclusivamente da "Vai alla fase successiva" oppure "Rimani alla fase corrente". Non scrivere nient'altro. Assicurati che le risposte finali siano come richiesto.
"""

prompt_stage2 = """
{messages}

Al momento, siamo in fase {stage}.
Dati i seguenti messaggi, dobbiamo capire se possiamo passare alla fase successiva o no.
In particolare, capiamo se nell'ultima fase:
1. Le domande totali del bambino siano state 3-4 circa;
2. Le domande siano state significative: il bambino ha chiesto domande coerenti, anche se non completamente corrette;

Prima ragiona. Poi, alla fine, scrivi "Risposta finale:" seguito esclusivamente da "Vai alla fase successiva" oppure "Rimani alla fase corrente". Non scrivere nient'altro. Assicurati che le risposte finali siano come richiesto.
"""

prompt_stage3 = """
{messages}

Al momento, siamo in fase {stage}.
Dati i seguenti messaggi, dobbiamo capire se possiamo passare alla fase successiva o no.
In particolare, capiamo se nell'ultima fase:
1. Il bambino abbia chiesto di chiarire 3-4 parole circa in totale;
2. Le richieste di chiarimento del bambino siano state significative: il bambino ha chiesto il significato di termini presenti nel testo, e non di termini qualsiasi non inerenti all'attività;

Prima ragiona. Poi, alla fine, scrivi "Risposta finale:" seguito esclusivamente da "Vai alla fase successiva" oppure "Rimani alla fase corrente". Non scrivere nient'altro. Assicurati che le risposte finali siano come richiesto.
"""

prompt_stage4 = """
{messages}

Al momento, siamo in fase {stage}.
Dati i seguenti messaggi, dobbiamo capire se possiamo passare alla fase successiva o no.
In particolare, capiamo se nell'ultima fase:
1. Il bambino abbia connesso la storia con 3-4 esperienze personali;
2. I collegamenti del bambino siano stati significativi: il bambino ha collegato la storia con esperienze personali, e non con esperienze inventate o non inerenti alla storia che abbiamo appena letto;

Prima ragiona. Poi, alla fine, scrivi "Risposta finale:" seguito esclusivamente da "Vai alla fase successiva" oppure "Rimani alla fase corrente". Non scrivere nient'altro. Assicurati che le risposte finali siano come richiesto.
"""