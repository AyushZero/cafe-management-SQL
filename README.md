# Cafe Management System

A simple, local web application built with Flask and SQLite to manage basic cafe operations like user roles (Admin, Employee, Customer), reservations, and orders.

## Features

* **User Roles:**
    * **Customer:** Can sign up, log in, make reservations, view past reservations, and view associated orders & loyalty points.
    * **Employee:** Can log in, add new customer accounts, add reservations for customers, and create orders (optionally linked to reservations).
    * **Admin:** Can log in and add new employee accounts.
* **Authentication:** Secure login/signup using password hashing.
* **Reservations:** Customers can book tables, and employees can manage reservations.
* **Orders:** Employees can create orders, optionally linking them to reservations. Basic loyalty points are awarded upon order completion if linked to a reservation.
* **Database:** Uses SQLite for simple, file-based data storage.
* **Local Deployment:** Runs entirely on your local machine using Flask's development server.

## Technology Stack

* **Backend:** Python, Flask
* **Database:** SQLite3
* **Frontend:** HTML, CSS
* **Environment Management:** venv

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd cafe_management_system
    ```
    *(Replace `<your-repository-url>` with the actual URL of your GitHub repository)*

2.  **Create and Activate Virtual Environment (Command Prompt):**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the Database (Integrated Terminal):**
    *(This creates the `cafe.db` file and sets up the necessary tables and default users. It's recommended to run this in your IDE's integrated terminal if available, ensuring the virtual environment is active.)*
    ```bash
    python init_db.py
    ```
    *Alternatively, you can run this command in the Command Prompt after activating the virtual environment.*

## Running the Application (Command Prompt)

1.  **Ensure your virtual environment is activated (see step 2 above).**
2.  **Navigate to the project directory:**
    ```bash
    cd cafe_management_system
    ```
3.  **Run the Flask app:**
    ```bash
    python app.py
    ```
4.  Open your web browser and navigate to: `http://127.0.0.1:5000` or `http://localhost:5000`

## Usage

* **Sign Up:** New users can sign up via the "Sign Up" link (they are created as 'customer' role).
* **Log In:** Use the login form. Default credentials (created by `init_db.py`):
    * **Admin:** `admin` / `adminpass`
    * **Employee:** `employee1` / `emppass`
    * **Customer:** `customer1` / `custpass`
* Navigate through the dashboard specific to your user role to access available features.

## Committing and Pushing Changes (Branch: master)

If you've made changes to the code and want to save them locally and share them with a remote repository (like GitHub), follow these steps in your Command Prompt or integrated terminal (ensure you are in the `cafe_management_system` directory):

1.  **Stage your changes:**
    ```bash
    git add .
    ```
    *(This adds all modified and new files to the staging area. To add specific files, use `git add <filename>`)*

2.  **Commit your changes:**
    ```bash
    git commit -m "Your descriptive commit message here"
    ```
    *(Replace `"Your descriptive commit message here"` with a clear and concise summary of the changes you've made.)*

3.  **Push your local commits to the remote repository (assuming your remote is named `origin` and your branch is `master`):**
    ```bash
    git push origin master
    ```
    *(You might be prompted for your username and password or a personal access token depending on your Git setup.)*

---

*Project created on April 15, 2025, in Chennai, Tamil Nadu, India.*