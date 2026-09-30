from loaders.sap090 import cargar_090

df = cargar_090("data/090.xlsx")

print()

print(df.head())

print()

print(df.columns.tolist())