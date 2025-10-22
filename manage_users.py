#!/usr/bin/env python
"""Script to manage users"""

from models import get_session, User, init_database

def create_new_users():
    """Create new users"""

    init_database()
    session = get_session()

    new_users = [
        {'username': 'EmilS', 'password': 'EmilS_2025!Pass'},
        {'username': 'IlgamH', 'password': 'Secure#IlgamH@2025'},
        {'username': 'MaratS', 'password': 'MaratS!Strong#99'},
        {'username': 'AlbertA', 'password': 'Albert@Secure2025!'},
        {'username': 'AndreyM', 'password': 'Andrey#Pass2025$'},
        {'username': 'RuslanS', 'password': 'Ruslan!Secure#77'},
        {'username': 'AdelyaZ', 'password': 'Adelya@Strong2025!'},
        {'username': 'IlizaZ', 'password': 'Iliza#Pass2025$'},
    ]

    try:
        # Create or update users
        for user_data in new_users:
            existing = session.query(User).filter_by(username=user_data['username']).first()

            if existing:
                # Update password
                existing.set_password(user_data['password'])
                print(f"Updated password for user: {user_data['username']}")
            else:
                # Create new user
                user = User(username=user_data['username'])
                user.set_password(user_data['password'])
                session.add(user)
                print(f"Created user: {user_data['username']} (password: {user_data['password']})")

        # Delete old users
        old_users = ['owner', 'teamlead', 'member']
        for username in old_users:
            user = session.query(User).filter_by(username=username).first()
            if user:
                session.delete(user)
                print(f"Deleted user: {username}")

        session.commit()
        print("\n=== User management completed ===")
        print("\n=== New Login Credentials ===")
        for user_data in new_users:
            print(f"{user_data['username']}: {user_data['password']}")

    except Exception as e:
        session.rollback()
        print(f"Error managing users: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    create_new_users()
