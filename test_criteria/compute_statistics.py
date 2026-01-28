import pandas as pd
import os
from sklearn.metrics import classification_report
import warnings
warnings.filterwarnings("ignore")

mapping = {
	"p": "prediction",
	"c": "clarification",
	"pd": "making questions (questioning)",
	"i": "inferential questioning",
	"r": "summary"
}

targets, predictions, phases = [], [], [] # target: data annotated by humans; predictions: predictions of CLAIRE
for filename in os.listdir("./"):
	if not filename.endswith(".xlsx"):
		continue
	df = pd.read_excel(filename)
	number_columns = len(df.columns)
	if number_columns == 9:
		target_column = -2
		prediction_column = -6
		phases_column = -3
	elif number_columns == 10:
		target_column = -3
		prediction_column = -7
		phases_column = -4
	else:
		raise ValueError(f"wrong number of columns for file {filename}: {number_columns}")

	for i,_ in df.iterrows():
		targets.append(df.iloc[i, target_column].lower().strip())
		predictions.append(df.iloc[i, prediction_column].lower().strip())
		phases.append(str(df.iloc[i, phases_column]).lower().strip())

print("Total performance")
print(classification_report(targets, predictions, digits=4))

print("Performance per phase")
for phase_name in set(phases):
	phase_targets, phase_predictions = [], []
	for i,phase in enumerate(phases):
		if phase == phase_name:
			phase_targets.append(targets[i])
			phase_predictions.append(predictions[i])
	print(f"\t- {mapping[phase_name]}")
	print(classification_report(phase_targets, phase_predictions, digits=4))

