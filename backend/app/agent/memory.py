import json

from sqlalchemy.orm import Session

from app.models import UserPreference


def get_preferences(db: Session, user_id: int) -> dict:
    rows = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()
    prefs = {}
    for row in rows:
        try:
            prefs[row.key] = json.loads(row.value_json)
        except json.JSONDecodeError:
            prefs[row.key] = row.value_json
    return prefs


def set_preference(db: Session, user_id: int, key: str, value: str) -> dict:
    # Store as JSON when the value already looks like JSON (list/dict/number/bool),
    # otherwise store as a plain JSON string so get_preferences round-trips cleanly.
    try:
        json.loads(value)
        value_json = value
    except json.JSONDecodeError:
        value_json = json.dumps(value)

    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.key == key)
        .first()
    )
    if row is None:
        row = UserPreference(user_id=user_id, key=key, value_json=value_json)
        db.add(row)
    else:
        row.value_json = value_json
    db.commit()
    return {"key": key, "value": json.loads(value_json)}
