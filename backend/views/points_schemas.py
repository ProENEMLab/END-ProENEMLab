class PointsHistorySchema:

    def dump(self, payload: dict) -> dict:
        body = dict(payload)
        body["items"] = [item.to_dict() for item in payload["items"]]
        return body
