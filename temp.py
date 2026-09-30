import pandas as pd

df = pd.read_excel("data/090.xlsx")

print(df.head())

print()
print(df.columns.tolist())