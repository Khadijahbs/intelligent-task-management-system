import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)


# =========================================================
# PRODUCTIVITY TRAINING DATA
# =========================================================
# This is synthetic training data created for development
# and testing of the productivity prediction component.
#
# Classes:
# High     = 20 records
# Moderate = 20 records
# Low      = 20 records
#
# Total    = 60 records
# =========================================================

data = {

    "completion_rate": [
        # HIGH
        98, 96, 94, 92, 90,
        89, 87, 85, 83, 81,
        80, 79, 77, 75, 73,
        72, 70, 68, 66, 64,

        # MODERATE
        70, 68, 66, 64, 62,
        60, 58, 57, 55, 53,
        52, 50, 48, 46, 45,
        43, 42, 40, 38, 36,

        # LOW
        45, 43, 41, 39, 37,
        35, 33, 31, 29, 27,
        25, 23, 21, 20, 18,
        16, 14, 12, 10, 8
    ],

    "on_time_rate": [
        # HIGH
        98, 96, 94, 91, 89,
        87, 85, 83, 81, 79,
        77, 75, 73, 71, 69,
        67, 65, 63, 61, 59,

        # MODERATE
        68, 66, 64, 62, 60,
        58, 56, 54, 52, 50,
        48, 46, 44, 42, 40,
        38, 36, 34, 32, 30,

        # LOW
        40, 38, 36, 34, 32,
        30, 28, 26, 24, 22,
        20, 18, 16, 14, 12,
        10, 9, 8, 6, 5
    ],

    "pending_rate": [
        # HIGH
        2, 4, 6, 8, 10,
        11, 13, 15, 17, 19,
        20, 21, 23, 25, 27,
        28, 30, 32, 34, 36,

        # MODERATE
        30, 32, 34, 36, 38,
        40, 42, 43, 45, 47,
        48, 50, 52, 54, 55,
        57, 58, 60, 62, 64,

        # LOW
        55, 57, 59, 61, 63,
        65, 67, 69, 71, 73,
        75, 77, 79, 80, 82,
        84, 86, 88, 90, 92
    ],

    "total_tasks": [
        # HIGH
        30, 29, 28, 27, 26,
        25, 24, 23, 22, 21,
        20, 19, 18, 17, 16,
        15, 14, 13, 12, 11,

        # MODERATE
        20, 19, 18, 17, 16,
        15, 14, 13, 12, 11,
        10, 10, 9, 9, 8,
        8, 7, 7, 6, 6,

        # LOW
        15, 14, 13, 12, 11,
        10, 10, 9, 9, 8,
        8, 7, 7, 6, 6,
        5, 5, 4, 4, 3
    ],

    "productivity": [

        # HIGH - 20 records
        "High", "High", "High", "High", "High",
        "High", "High", "High", "High", "High",
        "High", "High", "High", "High", "High",
        "High", "High", "High", "High", "High",

        # MODERATE - 20 records
        "Moderate", "Moderate", "Moderate", "Moderate", "Moderate",
        "Moderate", "Moderate", "Moderate", "Moderate", "Moderate",
        "Moderate", "Moderate", "Moderate", "Moderate", "Moderate",
        "Moderate", "Moderate", "Moderate", "Moderate", "Moderate",

        # LOW - 20 records
        "Low", "Low", "Low", "Low", "Low",
        "Low", "Low", "Low", "Low", "Low",
        "Low", "Low", "Low", "Low", "Low",
        "Low", "Low", "Low", "Low", "Low"
    ]
}


df = pd.DataFrame(data)


# =========================================================
# MODEL FILE PATH
# =========================================================

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "productivity_model.pkl"
)


# =========================================================
# TRAIN PRODUCTIVITY MODELS
# =========================================================

def train_productivity_model():

    print("\n========================================")
    print("PRODUCTIVITY MODEL TRAINING")
    print("========================================")

    X = df[
        [
            "completion_rate",
            "on_time_rate",
            "pending_rate",
            "total_tasks"
        ]
    ]

    y = df["productivity"]

    print("\nDataset size:", len(df))
    print("\nClass distribution:")
    print(y.value_counts())

    # -----------------------------------------------------
    # TRAIN / TEST SPLIT
    # -----------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print("\nTraining records:", len(X_train))
    print("Testing records:", len(X_test))

    # -----------------------------------------------------
    # MODELS
    # -----------------------------------------------------

    models = {

        "Decision Tree": DecisionTreeClassifier(
            random_state=42,
            max_depth=4
        ),

        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=5
        ),

        "Logistic Regression": Pipeline([
            (
                "scaler",
                StandardScaler()
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42
                )
            )
        ]),

        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
    }

    # -----------------------------------------------------
    # MODEL EVALUATION
    # -----------------------------------------------------

    results = []

    trained_models = {}

    for model_name, model in models.items():

        print("\n----------------------------------------")
        print(model_name)
        print("----------------------------------------")

        model.fit(
            X_train,
            y_train
        )

        y_pred = model.predict(
            X_test
        )

        accuracy = accuracy_score(
            y_test,
            y_pred
        )

        precision = precision_score(
            y_test,
            y_pred,
            average="macro",
            zero_division=0
        )

        recall = recall_score(
            y_test,
            y_pred,
            average="macro",
            zero_division=0
        )

        f1 = f1_score(
            y_test,
            y_pred,
            average="macro",
            zero_division=0
        )

        print(
            f"Accuracy:  {accuracy:.4f}"
        )

        print(
            f"Precision: {precision:.4f}"
        )

        print(
            f"Recall:    {recall:.4f}"
        )

        print(
            f"F1-score:  {f1:.4f}"
        )

        print("\nClassification Report:")

        print(
            classification_report(
                y_test,
                y_pred,
                zero_division=0
            )
        )

        print("Confusion Matrix:")

        print(
            confusion_matrix(
                y_test,
                y_pred,
                labels=[
                    "High",
                    "Moderate",
                    "Low"
                ]
            )
        )

        results.append({
            "Model": model_name,
            "Accuracy": accuracy,
            "Precision": precision,
            "Recall": recall,
            "F1_Score": f1
        })

        trained_models[
            model_name
        ] = model

    # -----------------------------------------------------
    # MODEL COMPARISON
    # -----------------------------------------------------

    results_df = pd.DataFrame(
        results
    )

    results_df = results_df.sort_values(
        by=[
            "F1_Score",
            "Accuracy"
        ],
        ascending=False
    ).reset_index(
        drop=True
    )

    print("\n========================================")
    print("MODEL COMPARISON")
    print("========================================")

    print(
        results_df.to_string(
            index=False
        )
    )

    # -----------------------------------------------------
    # SELECT BEST MODEL
    # -----------------------------------------------------

    best_model_name = results_df.iloc[0]["Model"]

    best_model = trained_models[
        best_model_name
    ]

    print("\n========================================")
    print(
        "BEST MODEL:",
        best_model_name
    )
    print("========================================")

    # -----------------------------------------------------
    # SAVE BEST MODEL
    # -----------------------------------------------------

    joblib.dump(
        best_model,
        MODEL_PATH
    )

    print(
        "\nBest productivity model saved successfully."
    )

    print(
        "Model path:",
        MODEL_PATH
    )

    return best_model


# =========================================================
# LOAD SAVED MODEL
# =========================================================

def load_productivity_model():

    if not os.path.exists(
        MODEL_PATH
    ):

        print(
            "\nNo trained productivity model found."
        )

        print(
            "Training a new model..."
        )

        return train_productivity_model()

    return joblib.load(
        MODEL_PATH
    )


# =========================================================
# PRODUCTIVITY PREDICTION
# =========================================================

def predict_productivity(
    completion_rate,
    on_time_rate,
    pending_rate,
    total_tasks
):
    """
    Predict productivity level using
    the selected trained machine-learning model.
    """

    model = load_productivity_model()

    input_data = pd.DataFrame([{

        "completion_rate":
            completion_rate,

        "on_time_rate":
            on_time_rate,

        "pending_rate":
            pending_rate,

        "total_tasks":
            total_tasks

    }])

    prediction = model.predict(
        input_data
    )

    return prediction[0]


# =========================================================
# RUN TRAINING WHEN FILE IS EXECUTED DIRECTLY
# =========================================================

if __name__ == "__main__":

    train_productivity_model()