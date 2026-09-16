"""Local administrator provisioning: python -m app.manage create-admin EMAIL."""
import argparse
from getpass import getpass
from sqlalchemy import func
from .database import SessionLocal
from . import models, schemas, utils


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create-admin'])
    parser.add_argument('email')
    parser.add_argument('--name', default='Administrator')
    args = parser.parse_args()
    with SessionLocal() as db:
        existing = db.query(models.User).filter(func.lower(models.User.email) == args.email.lower()).first()
        if existing:
            existing.isadmin = True
        else:
            password = getpass('New admin password (8–72 UTF-8 bytes): ')
            if password != getpass('Confirm password: '):
                parser.error('Passwords do not match')
            user = schemas.UserCreate(name=args.name, email=args.email, password=password)
            db.add(models.User(name=user.name, email=user.email, password=utils.hash(password), isadmin=True))
        utils.commit(db)
    print('Administrator account is ready.')


if __name__ == '__main__':
    main()
