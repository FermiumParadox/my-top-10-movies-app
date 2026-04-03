from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MOVIE_API_KEY")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap5(app)

# CREATE DB
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    trailer: Mapped[str] = mapped_column(String(250), nullable=True)


with app.app_context():
    db.create_all()

# Form Class
class RateMovieForm(FlaskForm):
    rating = StringField("Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")

class AddMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")

@app.route("/")
def home():
    movies = db.session.execute(
        db.select(Movie).order_by(Movie.rating.desc())
    ).scalars().all()

    for i in range(len(movies)):
        movies[i].ranking = i + 1

    db.session.commit()

    return render_template("index.html", movies=movies)

@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddMovieForm()

    if form.validate_on_submit():
        movie_title = form.title.data

        response = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={
                "api_key": API_KEY,
                "query": movie_title
            }
        )

        data = response.json()
        movies = data["results"]

        return render_template("select.html", movies=movies)

    return render_template("add.html", form=form)

@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")

    response = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_api_id}",
        params={"api_key": API_KEY}
    )

    data = response.json()

    video_response = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_api_id}/videos",
        params={"api_key": API_KEY}
    )

    video_data = video_response.json()
    print(video_data)

    trailer_key = None

    # Prefer official YouTube trailers
    for video in video_data["results"]:
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            trailer_key = video["key"]
            break

    # If none found, try teasers
    if trailer_key is None:
        for video in video_data["results"]:
            if video["site"] == "YouTube" and video["type"] == "Teaser":
                trailer_key = video["key"]
                break

    # CREATE MOVIE AFTER TRAILER IS FOUND
    new_movie = Movie(
        title=data["title"],
        year=data["release_date"].split("-")[0],
        img_url=f"https://image.tmdb.org/t/p/w500{data['poster_path']}",
        description=data["overview"],
        trailer=trailer_key
    )

    db.session.add(new_movie)
    db.session.commit()

    return redirect(url_for("rate_movie", id=new_movie.id))

@app.route("/edit", methods=["GET", "POST"])
def rate_movie():
    form = RateMovieForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie, form=form)


@app.route("/delete/<int:id>")
def delete(id):
    movie = db.get_or_404(Movie, id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
