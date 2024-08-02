import pandas as pd
from sklearn.linear_model import RidgeClassifier
from sklearn.feature_selection import SequentialFeatureSelector
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score

# Load the dataset
df = pd.read_csv("nba_games.csv", index_col=0)

# Prepare the dataset
df = df.sort_values("date")
df = df.reset_index(drop=True)
df = df.drop(columns=["mp.1", "mp_opp.1", "index_opp"])

# Add target column
def add_target(group):
    group["target"] = group["won"].shift(-1)
    return group

df = df.groupby("team", group_keys=False).apply(add_target)
df["target"].fillna(2, inplace=True)
df["target"] = df["target"].astype(int, errors="ignore")

# Remove columns with null values
nulls = pd.isnull(df).sum()
nulls = nulls[nulls > 0]
valid_columns = df.columns[~df.columns.isin(nulls.index)]
df = df[valid_columns].copy()

# Define the features to be used
removed_columns = ["season", "date", "won", "target", "team", "team_opp"]
selected_columns = df.columns[~df.columns.isin(removed_columns)]

# Normalize the data
scaler = MinMaxScaler()
df[selected_columns] = scaler.fit_transform(df[selected_columns])

# Feature Selection
rr = RidgeClassifier(alpha=1)
split = TimeSeriesSplit(n_splits=3)

sfs = SequentialFeatureSelector(rr, 
                                n_features_to_select=30, 
                                direction="forward",
                                cv=split,
                                n_jobs=1)
sfs.fit(df[selected_columns], df["target"])
predictors = list(selected_columns[sfs.get_support()])

# Backtesting function
def backtest(data, model, predictors, start=2, step=1):
    all_predictions = []
    seasons = sorted(data["season"].unique())
    
    for i in range(start, len(seasons), step):
        season = seasons[i]
        train = data[data["season"] < season]
        test = data[data["season"] == season]
        
        model.fit(train[predictors], train["target"])
        
        preds = model.predict(test[predictors])
        preds = pd.Series(preds, index=test.index)
        combined = pd.concat([test["target"], preds], axis=1)
        combined.columns = ["actual", "prediction"]
        
        all_predictions.append(combined)
    return pd.concat(all_predictions)

# Run backtesting
predictions = backtest(df, rr, predictors)

# Evaluate the model
accuracy = accuracy_score(predictions["actual"], predictions["prediction"])
print(f"Accuracy: {accuracy}")

# Analyze win rates based on whether the game was home or away
home_win_rate = df.groupby(["home"]).apply(lambda x: x[x["won"] == 1].shape[0] / x.shape[0])
print("Home win rates:")
print(home_win_rate)
