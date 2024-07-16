import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Load the data from Excel file
data = pd.read_excel('data.xlsx')

# Preprocess the data
data['Earnings_Date'] = pd.to_datetime(data['Earnings_Date'])
data['Buy_Date'] = pd.to_datetime(data['Buy_Date'])
data['Sell_Date'] = pd.to_datetime(data['Sell_Date'])
data['Gain'] = data['Total_Gain'] > 0

# Select features
features = ['Current_Price', 'Call_Strike', 'Put_Strike', 'Buy_Call_Price', 'Buy_Put_Price',
            'Call_Volume', 'Call_Open_Interest', 'Put_Volume', 'Put_Open_Interest']

X = data[features]
y = data['Gain']

# Handle missing values by imputing with the mean
imputer = SimpleImputer(strategy='mean')
X = imputer.fit_transform(X)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Define models
models = {
    'Logistic Regression': LogisticRegression(max_iter=1000),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
    'Hist Gradient Boosting': HistGradientBoostingClassifier(max_iter=100, random_state=42),
    'SVM': SVC(kernel='linear', probability=True)
}

# Evaluate each model using cross-validation
results = {}
for model_name, model in models.items():
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
    results[model_name] = np.mean(cv_scores)
    print(f"{model_name}: {np.mean(cv_scores):.4f}")

# Train and evaluate the best model
best_model_name = max(results, key=results.get)
best_model = models[best_model_name]
best_model.fit(X_train, y_train)
y_pred = best_model.predict(X_test)

# Print the results
accuracy = accuracy_score(y_test, y_pred)
print(f'Best Model: {best_model_name}')
print(f'Accuracy: {accuracy:.2f}')
print(classification_report(y_test, y_pred))

# Feature importance for tree-based models
if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    feature_importance = pd.Series(importances, index=features)
    plt.figure(figsize=(12, 8))
    feature_importance.sort_values(ascending=False).plot(kind='bar')
    plt.title('Feature Importance')
    plt.tight_layout()
    plt.show()

# Predict and filter out losing option straddles
data['Predicted_Gain'] = best_model.predict(imputer.transform(data[features]))
filtered_data = data[data['Predicted_Gain'] == 1]

# Save the filtered data to an Excel file
filtered_data.to_excel('final_stock_list_backtest.xlsx', index=False)

print(filtered_data)
