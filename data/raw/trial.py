import pandas as pd

df = pd.read_csv("bihar.csv")
new = df.head(100)  # or df.iloc[:100]
new.to_csv("few.csv", index=False)
