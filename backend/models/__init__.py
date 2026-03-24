from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .project import Project
from .page import Page
from .task import Task
from .reference_file import ReferenceFile
