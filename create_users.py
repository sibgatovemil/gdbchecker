#!/usr/bin/env python
"""Script to create initial users"""

from models import get_session, User, init_database

def create_initial_users():
    """Create three initial users: owner, teamlead, member"""

    # Initialize database first
    init_database()

    session = get_session()

    users_data = [
        {
            'username': 'owner',
            'password': 'OWN_Sec2025!Pass'
        },
        {
            'username': 'teamlead',
            'password': 'TL_Sec2025!Pass'
        },
        {
            'username': 'member',
            'password': 'MEM_Sec2025!Pass'
        }
    ]

    try:
        for user_data in users_data:
            # Check if user already exists
            existing = session.query(User).filter_by(username=user_data['username']).first()

            if existing:
                print(f"User '{user_data['username']}' already exists, skipping...")
                continue

            # Create new user
            user = User(username=user_data['username'])
            user.set_password(user_data['password'])
            session.add(user)
            print(f"Created user: {user_data['username']} (password: {user_data['password']})")

        session.commit()
        print("\nAll users created successfully!")
        print("\n=== Login Credentials ===")
        for user_data in users_data:
            print(f"{user_data['username']}: {user_data['password']}")

    except Exception as e:
        session.rollback()
        print(f"Error creating users: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    create_initial_users()
