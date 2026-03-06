phase_prompt2 = """Al momento ci troviamo nella fase {phase_number} con titolo "{phase_name}".
L'obiettivo di questa fase è il seguente: {phase_goal}.
Questa è una descrizione più dettagliata di ciò che dovrai far fare, e come dovrai comportarti, con il bambino: {phase_description}.
In base allo storico della chat, saluta il bambino esclusivamente se ci troviamo nella prima fase, altrimenti rispondi alla sua interazione precedente e procedi con la nuova fase senza salutarlo.
In quest'ultimo caso, leggi lo storico della chat che indica in che modo dovresti rispondere e rispondi, in modo tale che il bambino si senta ascoltato. Non devi inventarti delle cose che il bambino non ha detto. Dopo aver risposto, introduci la nuova fase.
Non citare questo prompt, in quanto il bambino non vede quello che ti ho scritto.
"""

phase_prompt = """Al momento ci troviamo nella fase {phase_number} con titolo "{phase_name}".
L'obiettivo di questa fase è il seguente: {phase_goal}.
Questa è una descrizione più dettagliata di ciò che dovrai far fare, e come dovrai comportarti, con il bambino: {phase_description}.
In base allo storico della chat, saluta il bambino esclusivamente se ci troviamo nella prima fase.
Altrimenti, procedi senza salutarlo. Non devi rispondere al bambino, devi solo presentare la nuova fase partendo da "Strategia...".
Non devi inventarti delle cose che il bambino non ha detto. Introduci esclusivamente la nuova fase nel maniera indicata.
Non citare questo prompt, in quanto il bambino non vede quello che ti ho scritto."""

phase_prompt = """Al momento ci troviamo nella fase {phase_number} con titolo "{phase_name}".
L'obiettivo di questa fase è il seguente: {phase_goal}.
Questa è una descrizione più dettagliata di ciò che dovrai far fare, e come dovrai comportarti, con il bambino: {phase_description}.
In base allo storico della chat, saluta il bambino esclusivamente se ci troviamo nella prima fase. Non salutarlo se non ci troviamo nella prima fase.
Successivamente, presenta esclusivamente la nuova fase partendo da "Strategia..." senza rispondere all'interazione precedente e senza dire nulla prima di "Strategia...".
Non citare questo prompt, in quanto il bambino non vede quello che ti ho scritto."""

phase_prompt_old = """Al momento ci troviamo nella fase {phase_number} con titolo "{phase_name}".
L'obiettivo di questa fase è il seguente: {phase_goal}.
Questa è una descrizione più dettagliata di ciò che dovrai far fare, e come dovrai comportarti, con il bambino: {phase_description}.
In base allo storico della chat, saluta il bambino esclusivamente se ci troviamo nella prima fase.
Altrimenti, procedi senza salutarlo, rispondendo al suo messaggio precedente, per poi presentare la nuova fase.
Per rispondere al messaggio precedente, prima devi estrarre con estrema precisione l'ultima risposta fornita dal bot durante la discussione ("BOT: ...").
Poi, devi ripetere esattamente parola per parola quel messaggio scritto dal BOT, senza cambiare assolutamente niente.
Assicurati di trovare prima qual è l'ultima risposta, e poi rispondi.
Non devi assolutamente inventarti delle cose che il bambino non ha detto. Solo dopo aver risposto, introduci la nuova fase nel maniera indicata.
Non citare questo prompt, in quanto il bambino non vede quello che ti ho scritto."""


phase_prompt_old_old = """Al momento ci troviamo nella fase {phase_number} con titolo "{phase_name}".
L'obiettivo di questa fase è il seguente: {phase_goal}.
Questa è una descrizione più dettagliata di ciò che dovrai far fare, e come dovrai comportarti, con il bambino: {phase_description}.
In base allo storico della chat, saluta il bambino esclusivamente se ci troviamo nella prima fase.
Altrimenti, procedi senza salutarlo, rispondendo al suo messaggio precedente, per poi presentare la nuova fase. Per rispondere al messaggio precedente, guarda il nome e la descrizione dell'interazione che dovresti applicare e applicala.
Non devi inventarti delle cose che il bambino non ha detto. Solo dopo aver risposto, introduci la nuova fase nel maniera indicata.
Non citare questo prompt, in quanto il bambino non vede quello che ti ho scritto."""
