import streamlit as st

def show_login_page(roster):
    """Displays the login page and handles authentication logic."""
    st.title("Welcome to Success Coach 🎓")
    st.write("Please select your role and log in to continue.")

    # Select Role
    role = st.radio("I am a:", ("Student", "Coach"), horizontal=True)

    with st.form("login_form"):
        if role == "Student":
            student_name = st.text_input("Full Name")
            student_id = st.text_input("Student ID (e.g., STU001)")
        else:
            st.info("Coach access is currently open for this demo.")
            # In a future update, you could add a password field here!

        submit = st.form_submit_button("Login")

    # Handle the login logic when the button is pressed
    if submit:
        if role == "Student":
            if not student_id or not student_name:
                st.error("Please enter both your Name and Student ID.")
            else:
                # Check if the student ID exists in the Google Sheet roster
                if roster is not None and student_id in roster['student_id'].astype(str).values:
                    # Save the user's data to Streamlit's temporary session memory
                    st.session_state.logged_in = True
                    st.session_state.role = "student"
                    st.session_state.student_id = student_id
                    st.session_state.student_name = student_name
                    st.rerun() # Refresh the page to bypass the login screen
                else:
                    st.error(f"Could not find Student ID '{student_id}' in the system.")
                    
        elif role == "Coach":
            st.session_state.logged_in = True
            st.session_state.role = "coach"
            st.rerun() # Refresh the page to bypass the login screen