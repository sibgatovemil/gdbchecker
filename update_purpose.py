#!/usr/bin/env python
"""Script to update Purpose field in domains"""

from models import get_session, Domain

def update_purpose():
    """Update purpose values for domains"""

    session = get_session()

    try:
        # Update all domains with old purpose value
        updated = session.query(Domain).filter(
            Domain.purpose == 'Домен редиректор офферов'
        ).update(
            {Domain.purpose: 'Редиректор офферов'},
            synchronize_session=False
        )

        print(f"Updated {updated} domains: 'Домен редиректор офферов' -> 'Редиректор офферов'")

        # Update specific domain
        specific_domain = session.query(Domain).filter_by(
            domain='9wu8vx76.assterteam.com'
        ).first()

        if specific_domain:
            specific_domain.purpose = 'Домен бинома'
            print(f"Updated domain {specific_domain.domain}: purpose = 'Домен бинома'")
        else:
            print("Domain 9wu8vx76.assterteam.com not found")

        session.commit()
        print("\n✅ Purpose update completed successfully")

    except Exception as e:
        session.rollback()
        print(f"❌ Error updating purpose: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    update_purpose()
