import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta

DATA_PATH = "data/flashcards.csv"

st.set_page_config(
    page_title="SmartRecall",
    page_icon="🧠",
    layout="wide"
)

COLUMNS = [
    "card_id", "question", "answer", "subject", "difficulty",
    "last_reviewed", "next_review", "review_count",
    "correct_count", "memory_strength", "status"
]


def load_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)

    df = pd.read_csv(DATA_PATH)

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["last_reviewed"] = df["last_reviewed"].astype("object")
    df["next_review"] = df["next_review"].astype("object")

    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0).astype(int)
    df["correct_count"] = pd.to_numeric(df["correct_count"], errors="coerce").fillna(0).astype(int)
    df["memory_strength"] = pd.to_numeric(df["memory_strength"], errors="coerce").fillna(1.0)

    return df[COLUMNS]


def save_data(df):
    df.to_csv(DATA_PATH, index=False)


def calculate_status(memory_strength):
    if memory_strength < 3:
        return "Learning"
    elif memory_strength <= 6:
        return "Reviewing"
    else:
        return "Mastered"


df = load_data()

st.title("🧠 SmartRecall")
st.subheader("AI-Based Flashcard Forgetting Curve Engine")

menu = st.sidebar.radio(
    "Navigation",
    ["Home", "Add Flashcard", "Review Flashcards", "Analytics"]
)

if menu == "Home":
    st.header("Dashboard")

    total_cards = len(df)

    if total_cards > 0:
        temp_df = df.copy()
        temp_df["next_review_date"] = pd.to_datetime(
            temp_df["next_review"],
            errors="coerce"
        ).dt.date

        due_today = len(temp_df[temp_df["next_review_date"] <= date.today()])
        mastered = len(df[df["status"] == "Mastered"])
        learning = len(df[df["status"] == "Learning"])
        reviewing = len(df[df["status"] == "Reviewing"])
    else:
        due_today = 0
        mastered = 0
        learning = 0
        reviewing = 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Cards", total_cards)
    col2.metric("Due Today", due_today)
    col3.metric("Learning", learning)
    col4.metric("Mastered", mastered)

    st.write("### Study Status")
    st.write(f"Reviewing Cards: {reviewing}")

    st.info("Use the sidebar to add and review flashcards.")


elif menu == "Add Flashcard":
    st.header("Add New Flashcard")

    with st.form("flashcard_form"):
        question = st.text_area("Question")
        answer = st.text_area("Answer")
        subject = st.text_input("Subject / Topic")
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])

        submitted = st.form_submit_button("Add Flashcard")

        if submitted:
            if question.strip() == "" or answer.strip() == "" or subject.strip() == "":
                st.error("Please fill all fields.")
            else:
                if len(df) == 0:
                    new_id = 1
                else:
                    new_id = int(df["card_id"].max()) + 1

                new_card = {
                    "card_id": new_id,
                    "question": question,
                    "answer": answer,
                    "subject": subject,
                    "difficulty": difficulty,
                    "last_reviewed": "",
                    "next_review": str(date.today()),
                    "review_count": 0,
                    "correct_count": 0,
                    "memory_strength": 1.0,
                    "status": "Learning"
                }

                df = pd.concat([df, pd.DataFrame([new_card])], ignore_index=True)
                save_data(df)

                st.success("Flashcard added successfully!")


elif menu == "Review Flashcards":
    st.header("Review Flashcards")

    if len(df) == 0:
        st.info("No flashcards available. Add some first.")
    else:
        review_df = df.copy()
        review_df["next_review_date"] = pd.to_datetime(
            review_df["next_review"],
            errors="coerce"
        ).dt.date

        due_cards = review_df[review_df["next_review_date"] <= date.today()]

        if len(due_cards) == 0:
            st.success("No cards due today. Great job!")
        else:
            card_index = due_cards.index[0]
            card = df.loc[card_index]

            st.subheader("Question")
            st.write(card["question"])

            with st.expander("Show Answer"):
                st.write(card["answer"])

            st.write("How well did you remember this?")

            def update_review(response):
                memory_strength = float(df.loc[card_index, "memory_strength"])

                if response == "Forgot":
                    interval = 1
                    memory_strength = max(1, memory_strength - 0.5)

                elif response == "Hard":
                    interval = 2
                    memory_strength += 0.5
                    df.loc[card_index, "correct_count"] = int(df.loc[card_index, "correct_count"]) + 1

                elif response == "Good":
                    interval = 4
                    memory_strength += 1
                    df.loc[card_index, "correct_count"] = int(df.loc[card_index, "correct_count"]) + 1

                else:
                    interval = 7
                    memory_strength += 2
                    df.loc[card_index, "correct_count"] = int(df.loc[card_index, "correct_count"]) + 1

                df.loc[card_index, "last_reviewed"] = str(date.today())
                df.loc[card_index, "next_review"] = str(date.today() + timedelta(days=interval))
                df.loc[card_index, "review_count"] = int(df.loc[card_index, "review_count"]) + 1
                df.loc[card_index, "memory_strength"] = memory_strength
                df.loc[card_index, "status"] = calculate_status(memory_strength)

                save_data(df)

                st.success(f"Review saved! Next review after {interval} day(s).")
                st.rerun()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("Forgot"):
                    update_review("Forgot")

            with col2:
                if st.button("Hard"):
                    update_review("Hard")

            with col3:
                if st.button("Good"):
                    update_review("Good")

            with col4:
                if st.button("Easy"):
                    update_review("Easy")


elif menu == "Analytics":
    st.header("Analytics")

    if len(df) == 0:
        st.info("No data available yet.")
    else:
        total_reviews = df["review_count"].sum()
        total_correct = df["correct_count"].sum()

        if total_reviews > 0:
            accuracy = (total_correct / total_reviews) * 100
        else:
            accuracy = 0

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Reviews", int(total_reviews))
        col2.metric("Correct Reviews", int(total_correct))
        col3.metric("Accuracy", f"{accuracy:.2f}%")

        st.write("### Subject-wise Cards")
        st.bar_chart(df["subject"].value_counts())

        st.write("### Difficulty-wise Cards")
        st.bar_chart(df["difficulty"].value_counts())

        st.write("### Status-wise Cards")
        st.bar_chart(df["status"].value_counts())

        st.write("### Full Flashcard Data")
        st.dataframe(df)