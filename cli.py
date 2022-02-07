import click
from application import init_app
from application.auth import create_user, delete_user

app = init_app()

@app.cli.command('create-user')
@click.argument('username', nargs=1, required=True)
@click.argument('password', nargs=1, required=True)
def create_new_user(username, password):
    create_user(username, password)

@app.cli.command('remove-user')
@click.argument('username', nargs=1, required=True)
def remove_user(username):
    delete_user(username)
    