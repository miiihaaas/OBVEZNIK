"""Flask CLI commands for application management."""
import click
from flask.cli import with_appcontext
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
import getpass


@click.command('create-admin')
@click.option('--email', prompt='Admin Email', help='Email address for admin user')
@click.option('--full-name', prompt='Full Name', help='Full name of admin user')
@with_appcontext
def create_admin_command(email, full_name):
    """
    Create a new admin user.

    Usage:
        flask create-admin
        flask create-admin --email admin@example.com --full-name "Admin User"
    """
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        click.echo(click.style(f'[ERROR] Korisnik sa email-om {email} vec postoji!', fg='red'))
        return

    # Prompt for password (hidden input)
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)

    # Create admin user
    admin = User(
        email=email,
        full_name=full_name,
        role='admin',
        is_active=True
    )
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    click.echo(click.style(f'[SUCCESS] Admin korisnik {email} uspesno kreiran!', fg='green'))
    click.echo(f'   ID: {admin.id}')
    click.echo(f'   Email: {admin.email}')
    click.echo(f'   Full Name: {admin.full_name}')
    click.echo(f'   Role: {admin.role}')


@click.command('create-pausalac')
@click.option('--email', prompt='Paušalac Email', help='Email address for pausalac user')
@click.option('--full-name', prompt='Full Name', help='Full name of pausalac user')
@click.option('--firma-id', prompt='Firma ID', type=int, help='ID of PausalnFirma')
@with_appcontext
def create_pausalac_command(email, full_name, firma_id):
    """
    Create a new pausalac user.

    Usage:
        flask create-pausalac
        flask create-pausalac --email pausalac@example.com --full-name "Pausalac User" --firma-id 1
    """
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        click.echo(click.style(f'[ERROR] Korisnik sa email-om {email} već postoji!', fg='red'))
        return

    # Check if firma exists
    firma = PausalnFirma.query.get(firma_id)
    if not firma:
        click.echo(click.style(f'[ERROR] Paušalna firma sa ID {firma_id} ne postoji!', fg='red'))
        return

    # Prompt for password (hidden input)
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)

    # Create pausalac user
    pausalac = User(
        email=email,
        full_name=full_name,
        role='pausalac',
        firma_id=firma_id,
        is_active=True
    )
    pausalac.set_password(password)

    db.session.add(pausalac)
    db.session.commit()

    click.echo(click.style(f'[OK] Paušalac korisnik {email} uspešno kreiran!', fg='green'))
    click.echo(f'   ID: {pausalac.id}')
    click.echo(f'   Email: {pausalac.email}')
    click.echo(f'   Full Name: {pausalac.full_name}')
    click.echo(f'   Role: {pausalac.role}')
    click.echo(f'   Firma: {firma.naziv} (ID: {firma.id})')


@click.command('list-users')
@with_appcontext
def list_users_command():
    """
    List all users in the system.

    Usage:
        flask list-users
    """
    users = User.query.order_by(User.created_at.desc()).all()

    if not users:
        click.echo(click.style('Nema korisnika u sistemu.', fg='yellow'))
        return

    click.echo(click.style(f'\n[INFO] Ukupno korisnika: {len(users)}\n', fg='cyan', bold=True))

    for user in users:
        role_color = 'red' if user.role == 'admin' else 'blue'
        status_icon = '[OK]' if user.is_active else '[ERROR]'

        click.echo(f'{status_icon} ID: {user.id} | {click.style(user.email, fg="green")} | {click.style(user.role.upper(), fg=role_color)}')
        click.echo(f'   Ime: {user.full_name}')
        if user.firma:
            click.echo(f'   Firma: {user.firma.naziv}')
        click.echo(f'   Kreiran: {user.created_at.strftime("%d.%m.%Y %H:%M")}')
        click.echo('')


@click.command('list-firme')
@with_appcontext
def list_firme_command():
    """
    List all paušalne firme in the system.

    Usage:
        flask list-firme
    """
    firme = PausalnFirma.query.order_by(PausalnFirma.naziv).all()

    if not firme:
        click.echo(click.style('Nema paušalnih firmi u sistemu.', fg='yellow'))
        return

    click.echo(click.style(f'\n[INFO] Ukupno firmi: {len(firme)}\n', fg='cyan', bold=True))

    for firma in firme:
        status_icon = '[OK]' if firma.is_active else '[ERROR]'

        click.echo(f'{status_icon} ID: {firma.id} | {click.style(firma.naziv, fg="green")}')
        click.echo(f'   PIB: {firma.pib}')
        click.echo(f'   Matični broj: {firma.maticni_broj}')
        click.echo(f'   Email: {firma.email}')
        click.echo(f'   Telefon: {firma.telefon}')
        click.echo('')


def register_commands(app):
    """Register all CLI commands with the Flask app."""
    app.cli.add_command(create_admin_command)
    app.cli.add_command(create_pausalac_command)
    app.cli.add_command(list_users_command)
    app.cli.add_command(list_firme_command)
