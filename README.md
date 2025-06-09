# GitHub Codespaces ♥️ Flask

Welcome to your shiny new Codespace running Flask! We've got everything fired up and running for you to explore Flask.
This project now contains a simple Customer Relationship Management (CRM) application
built with Flask and SQLite. It allows you to manage accounts, leads and contacts.

You've got a blank canvas to work on from a git perspective as well. There's a single initial commit with the what you're seeing right now - where you go from here is up to you!

Everything you do here is contained within this one codespace. There is no repository on GitHub yet. If and when you’re ready you can click "Publish Branch" and we’ll create your repository and push up your project. If you were just exploring then and have no further need for this code then you can simply delete your codespace and it's gone forever.

To run this application:

```
flask --debug run
```

Ensure dependencies are installed with:

```
pip install -r requirements.txt
```

The requirements pin `Werkzeug<3` to avoid an incompatibility between
Flask-Login and newer Werkzeug releases.

On first launch the application will create an SQLite database file named
`crm.db` in the project directory.
