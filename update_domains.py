#!/usr/bin/env python
"""Script to update all existing domains with added_by='EmilS'"""

from models import get_session, Domain

def update_existing_domains():
    """Set added_by='EmilS' for all domains where added_by is NULL"""

    session = get_session()

    try:
        # Update all domains where added_by is NULL
        updated = session.query(Domain).filter(Domain.added_by == None).update(
            {Domain.added_by: 'EmilS'},
            synchronize_session=False
        )

        session.commit()
        print(f"Updated {updated} domains with added_by='EmilS'")

    except Exception as e:
        session.rollback()
        print(f"Error updating domains: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    update_existing_domains()
