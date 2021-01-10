import os
#export FLASK_APP=application.py
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
#from flask_session.__init__ import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")



@app.route("/")
@login_required
def index():
    """Show tag history based on user"""
    user_id=session["user_id"]
    user_type = db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]

    # Supervisors will see tags submitted for approval
    if user_type==1:
        open_tags=db.execute("SELECT tag_id, color, date_created, status_code FROM tags JOIN status ON approval_status=status_id WHERE approval_status=1 ORDER BY date_created DESC")

        return render_template("index.html", open_tags=open_tags, user_type=user_type)

    # Trades and other users will see approved tags assigned to them
    elif user_type==2:
        open_tags=db.execute("SELECT tag_id, color, status_code FROM tags JOIN status ON completion_status=status_id WHERE user_id_to=:user_id AND approval_status=2 AND (completion_status=5 OR completion_status=4) ORDER BY completion_status DESC",
                        user_id=user_id)
        all_tags=db.execute("SELECT * FROM tags WHERE user_id_from=:user_id", user_id=user_id)
        return render_template("index.html", open_tags=open_tags, all_tags=all_tags, user_type=user_type)


@app.route("/tagSubmission", methods=["GET", "POST"])
@login_required
def tags():
    # This function takes the color from the insert.html dropdown list and generates a tag of that color
    if request.method=="GET":
        color=request.args.get("color")
        return render_template("tagSubmission.html", color=color)

@app.route("/check", methods=["GET"])
def check():
    username=request.args.get("username")
    rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

    # Ensure tag_id is unique
    if len(rows) != 0:
        registered=True
    else:
        registered=False

    return jsonify(registered)


@app.route("/tagcheck", methods=["GET"])
def tagcheck():
    # Checking to see if Tag ID entered is unique
    tagid=request.args.get("tagid")
    rows = db.execute("SELECT * FROM tags WHERE tag_id = :tagid", tagid=tagid)

    # Ensure tag_id is unique
    if len(rows) != 0:
        tag_exists=True
    else:
        tag_exists=False

    return jsonify(tag_exists)


@app.route("/tagHistory")
@login_required
def tagHistory():
    user_id=session["user_id"]
    user_type=db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]

    # Supervisors will see all tags they have approved and disapproved
    if user_type==1:
        tags=db.execute("SELECT tag_id, color, date_approved, status_code FROM tags JOIN status ON approval_status=status_id WHERE approved_by=:user_id AND (approval_status=2 OR approval_status=3) ORDER BY date_approved DESC",
            user_id=user_id)
        print(tags)
        status="Reviewed"
        return render_template("tagHistory.html", tags=tags, status=status, user_type=user_type)

    # Trades will see all tags they have completed or not completed
    elif user_type==2:
        tags=db.execute("SELECT tag_id, color, date_closed, status_code FROM tags JOIN status ON completion_status=status_id WHERE user_id_to=:user_id AND (completion_status=6 OR completion_status=7) ORDER BY date_closed DESC",
            user_id=user_id)
        status="Closed"
        return render_template("tagHistory.html", tags=tags, status=status, user_type=user_type)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()


    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return render_template("login.html", password="wrong")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/tagDisplay", methods=["GET", "POST"])
@login_required
def tagDisplay():
    # This Function displays any selected tag
    user_id=session["user_id"]
    tag_id=request.args.get("tagid")
    tag=db.execute("SELECT * FROM tags WHERE tag_id=:tag_id", tag_id=tag_id)[0]
    name=db.execute("SELECT name FROM tags JOIN users ON user_id_from=id WHERE tag_id=:tag_id", tag_id=tag_id)[0]["name"]
    user_type=db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]
    trades=db.execute("SELECT name FROM users WHERE user_type='2'")

    # Supervisors will be able to approve and disapprove tags
    if user_type==1:
        if tag["approval_status"]==2 or tag["approval_status"]==3:
            if tag["completion_status"]==6 or tag["completion_status"]==7:
                mode="displayCompleted"
            else:
                mode="display" # if tag has been approved or disapproved it can only be displayed

            assigned=db.execute("SELECT name FROM tags JOIN users ON user_id_to=id WHERE tag_id=:tag_id", tag_id=tag_id)[0]["name"]
            return render_template("tagDisplay.html", tag=tag, name=name, mode=mode, assigned=assigned, user_type=user_type)
        else:
            print("Unsafe Basic Condition#"+ tag["unsafeBasicCondition"]+"#")
            return render_template("tagApproval.html", tag=tag, name=name, trades=trades, user_type=user_type)

    # Trades will be able to change the status of their open tags and mark them as completed/not completed
    elif user_type==2:
        if tag["completion_status"]==4 or tag["completion_status"]==5:
            mode="change status"
        else:
            mode="displayCompleted" #if a tag has been marked complete or incomplete it can only be displayed
        assigned=db.execute("SELECT name FROM tags JOIN users ON user_id_to=id WHERE tag_id=:tag_id", tag_id=tag_id)[0]["name"]
        return render_template("tagDisplay.html", tag=tag, name=name, mode=mode, assigned=assigned, user_type=user_type)

@app.route("/passwordChange", methods=["GET", "POST"])
def register():
    """Register user"""


    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username=request.form.get("username")
        old_password=request.form.get("old_password")
        password=request.form.get("password")
        confirmation=request.form.get("confirmation")

        # Ensure username was submitted
        if confirmation != password:
            return render_template("passwordChange.html", flag="incorrect")


        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Ensure username exists and password is correct
        if len(rows) != 0:
            check_old_password=db.execute("SELECT * FROM users WHERE username=:username", username=username)[0]["password"]

            if old_password==check_old_password or check_password_hash(check_old_password, old_password):
                db.execute("UPDATE users SET password=:password WHERE username=:username",  password=generate_password_hash(password), username=username)

            else:
                return render_template("passwordChange.html", flag="incorrect")
        else:
            return render_template("passwordChange.html", flag="incorrect")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("passwordChange.html")





@app.route("/insert", methods=["GET", "POST"])
@login_required
def insert():
    user_id=session["user_id"]
    user_type = db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]


    # This function takes all the information from a Tag and stores in the SQL database
    if request.method == "GET":
        return render_template("insert.html", user_type=user_type)
    elif request.method == "POST":
        # Even thought the form is gerenrated by tagSubmission.html the 'POST' submission occurs in insert.html as the path is still '/insert'
        tag_id=request.form.get("tag_id")
        tag_rows=db.execute("SELECT * from tags WHERE tag_id=:tag_id", tag_id=tag_id)
        if len(tag_rows)!=0:
            return apology("Tag ID already exists")

        user_id=session["user_id"]
        color=request.form.get("color")
        hazard=request.form.get("hazard")
        line=request.form.get("line")
        area=request.form.get("area")
        equipment=request.form.get("equipment")
        date=datetime.datetime.today().strftime('%Y-%m-%d')

        a=request.form.get("unCondition")
        if a:
            unsafeCondition="yes"
        else:
            unsafeCondition="no"

        b=request.form.get("unBasicCondition")
        if b:
            unsafeBasicCondition="yes"
        else:
            unsafeBasicCondition="no"

        c=request.form.get("unItem")
        if c:
            unnecessaryItem="yes"
        else:
            unnecessaryItem="no"

        d=request.form.get("hardToAccess")
        if d:
            hardToAccess="yes"
        else:
            hardToAccess="no"

        e=request.form.get("sOfContamination")
        if e:
            sOfContamination="yes"
        else:
            sOfContamination="no"

        f=request.form.get('minorFlaw')
        if f:
            minorFlaw="yes"
        else:
            minorFlaw="no"

        g=request.form.get("quality")
        if g:
            quality="yes"
        else:
            quality="no"

        tagPriority=request.form.get("tagPriority")
        description=request.form.get("description")
        solution=request.form.get("solution")

        db.execute("INSERT INTO tags (tag_id, color, user_id_from, approval_status, hazard, line, area, equipment, unsafeCondition, unsafeBasicCondition, unnecessaryItem, hardToAccess, sOfContamination, minorFlaw, quality, tagPriority, description, solution, user_id_from, date_created) VALUES (:tag_id, :color, :user_id_from, :approval_status, :hazard, :line, :area, :equipment, :unsafeCondition, :unsafeBasicCondition, :unnecessaryItem, :hardToAccess, :sOfContamination, :minorFlaw, :quality, :tagPriority, :description, :solution, :user_id, :date)",
            tag_id=tag_id, color=color, user_id_from=user_id, approval_status=1, hazard=hazard, line=line, area=area, equipment=equipment, unsafeCondition=unsafeCondition, unsafeBasicCondition=unsafeBasicCondition, unnecessaryItem=unnecessaryItem, hardToAccess=hardToAccess, sOfContamination=sOfContamination, minorFlaw=minorFlaw, quality=quality, tagPriority=tagPriority, description=description, solution=solution, user_id=user_id, date=date)

        return render_template("success.html", user_type=user_type)


@app.route("/tagApproval", methods=["GET", "POST"])
@login_required
def approve():
    user_id=session["user_id"]
    user_type = db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]

    tag_id=request.args.get("tagid")
    if request.method == "POST":
        # If Tag is disapproved, it is deleted
        if request.form.get("approval")=="no":
            db.execute("DELETE FROM tags WHERE tag_id=:tag_id", tag_id=tag_id)
            return render_template("disapproved.html", tag_id=tag_id, user_type=user_type)

        # If Tag is approved it is assigned to said trade
        elif request.form.get("approval")=="yes":
            approver=session["user_id"]
            username_to=request.form.get("username_to")
            user_id_to=db.execute("SELECT id FROM users WHERE name=:username_to", username_to=username_to)[0]["id"]
            user_to=db.execute("SELECT name FROM users WHERE id=:user_id_to", user_id_to=user_id_to)[0]["name"]
            db.execute("UPDATE tags SET user_id_to=:user_id_to, approval_status='2', completion_status='4', approved_by=:approver, date_approved=:today WHERE tag_id=:tag_id",
                user_id_to=user_id_to, tag_id=tag_id, approver=approver, today=datetime.datetime.today().strftime('%Y-%m-%d'))
            return render_template("approved.html", tag_id=tag_id, user_to=user_to, user_type=user_type)

@app.route("/changeStatus", methods=["GET", "POST"])
@login_required
def status():
    tag_id=request.args.get("tagid")
    # Completes the status submission of their assigned tags
    if request.method=="POST":
        completion_status=request.form.get("tag_status")
        db.execute("UPDATE tags SET completion_status=:completion_status WHERE tag_id=:tag_id", completion_status=completion_status, tag_id=tag_id)
        if completion_status=='6' or completion_status=='7':
            db.execute("UPDATE tags SET date_closed=:today WHERE tag_id=:tag_id", today=datetime.datetime.today().strftime('%Y-%m-%d'), tag_id=tag_id)
        return redirect("/")

@app.route("/analytics", methods=["GET", "POST"])
@login_required
def analytics():
    user_id=session["user_id"]
    user_type = db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]

    date=datetime.datetime.today().strftime('%Y-%m-%d') # How to select today's date in python
    week=db.execute("SELECT strftime('%W','now')")[0] # How to select this week in sql

    # Selecting individual colored and total weekly approved tags by supervisors
    app_red=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_approved)=strftime('%W','now') AND color='Red' AND approval_status='2')")[0]
    app_blue=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_approved)=strftime('%W','now') AND color='Blue' AND approval_status='2')")[0]
    app_yellow=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_approved)=strftime('%W','now') AND color='Yellow' AND approval_status='2')")[0]
    weekly_approved_tags=[app_red['COUNT (*)'], app_blue['COUNT (*)'], app_yellow['COUNT (*)']]
    total_approved=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_approved)=strftime('%W','now') AND approval_status='2')")[0]

    # Selecting individual colored and total weekly completed tags by trades
    com_red=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_closed)=strftime('%W','now') AND color='Red' AND completion_status='6')")[0]
    com_blue=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_closed)=strftime('%W','now') AND color='Blue' AND completion_status='6')")[0]
    com_yellow=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_closed)=strftime('%W','now') AND color='Yellow' AND completion_status='6')")[0]
    weekly_completed_tags=[com_red['COUNT (*)'], com_blue['COUNT (*)'], com_yellow['COUNT (*)']]
    total_completed=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%W',date_closed)=strftime('%W','now') AND completion_status='6')")[0]

    thisMonth=int(datetime.datetime.today().strftime('%m'))
    monthly_completed_tags=[]
    monthly_approved_tags=[]
    completionRate=[]

    # Calculating monthly tag completion rate
    for i in range (thisMonth):

        completed=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%m',date_closed)=:month AND completion_status='6')", month='0'+str(i+1))[0]
        monthly_completed_tags.append(completed['COUNT (*)'])

        approved=db.execute("SELECT COUNT (*) FROM (SELECT tag_id FROM tags WHERE strftime('%m',date_approved)=:month AND approval_status='2')", month='0'+str(i+1))[0]
        monthly_approved_tags.append(approved['COUNT (*)'])

        if monthly_approved_tags[i]==0:
            completionRate.append(0)
        else:
            completionRate.append(monthly_completed_tags[i]/monthly_approved_tags[i])

    return render_template("analytics.html",
        weekly_approved_tags=weekly_approved_tags, weekly_completed_tags=weekly_completed_tags, completionRate=completionRate,total_approved=total_approved['COUNT (*)'], total_completed=total_completed['COUNT (*)'], user_type=user_type)

@app.route("/searchTags", methods=["GET", "POST"])
@login_required
def search():
    user_id=session["user_id"]
    user_type = db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]

    closed_tags=db.execute("SELECT tag_id, color, date_closed, status_code FROM tags JOIN status ON completion_status=status_id WHERE completion_status=6 OR completion_status=7 ORDER BY date_closed DESC")
    return render_template("searchTags.html", closed_tags=closed_tags, user_type=user_type)


@app.route("/openTags", methods=["GET", "POST"])
@login_required
def openTags():
    user_id=session["user_id"]
    user_type = db.execute("SELECT user_type FROM users WHERE id=:user_id", user_id=user_id)[0]["user_type"]

    open_tags=db.execute("SELECT tag_id, color, date_created, status_code FROM tags JOIN status ON completion_status=status_id WHERE completion_status=4 OR completion_status=5 ORDER BY date_created DESC")
    return render_template("openTags.html", open_tags=open_tags, user_type=user_type)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
