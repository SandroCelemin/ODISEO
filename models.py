def row_to_item(r):
    return {
        "id": r["id"],
        "item_id": r["item_id"],
        "user": r["user"],
        "have": r["have"],
        "description": r["description"],
        "image": r["image"],
        "want": r["want"],
        "category": r["category"],
        "status": r["status"]
    }