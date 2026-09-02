from services.utils import similarity

def first_distance_items(items, search, intent, threshold=0.6):

    if not search:
        return items

    search = search.lower().strip()
    scored = []

    for item in items:

        have = item["have"].lower()
        want = item["want"].lower()

        if intent == "have":     
            target = want
        elif intent == "want":
            target = have

        score = similarity(search, target)
        
        if score >= threshold:
            scored.append((score, item))
        """
        if similarity(search, target) >= threshold:
            scored.append((similarity(search, target), item))
        """
    scored.sort(key=lambda x: x[0], reverse=True) #ordena los obj que se muestran dependiendo de lo que se parece el objeto target al objeto intent

    return [item for _, item in scored]