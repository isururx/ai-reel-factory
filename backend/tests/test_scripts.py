from unittest.mock import patch
from app.models.page import Page, PageProfile
from app.models.trend import TrendItem, PageTrendRecommendation

def _seed(client):
    from app.database.session import get_db
    db = next(client.app.dependency_overrides[get_db]())
    page = Page(name="Science", owner_id="test-user-0001"); db.add(page); db.flush()
    db.add(PageProfile(page_id=page.id, niche="Science", target_audience="General audience"))
    trend = TrendItem(owner_id="test-user-0001", source_name="Test", source_url="https://example.com/story", title="A science discovery", summary="A source summary")
    db.add(trend); db.flush(); rec = PageTrendRecommendation(page_id=page.id, trend_id=trend.id, status="selected")
    db.add(rec); db.commit(); result=(page.id, rec.id); db.close(); return result

def test_generate_three_script_variations(client):
    page_id, rec_id = _seed(client)
    variations=[{"title":f"Variation {i}","hook":f"Hook {i}","narration":f"Narration {i}","caption":"Caption","hashtags":["#science"],"script_data":{"evaluation":{"hook_score":8}}} for i in range(1,4)]
    with patch("app.api.routes.scripts.generate_variations", return_value=variations):
        response=client.post(f"/api/v1/pages/{page_id}/trends/{rec_id}/generate-scripts")
    assert response.status_code == 201, response.text
    assert len(response.json()["versions"]) == 3

def test_cannot_generate_for_unselected_trend(client):
    page_id, rec_id = _seed(client)
    from app.database.session import get_db
    from app.models.trend import PageTrendRecommendation
    db=next(client.app.dependency_overrides[get_db]()); db.get(PageTrendRecommendation,rec_id).status="saved"; db.commit(); db.close()
    assert client.post(f"/api/v1/pages/{page_id}/trends/{rec_id}/generate-scripts").status_code == 404

def test_edit_creates_new_version(client):
    page_id, rec_id = _seed(client)
    variations=[{"title":f"Variation {i}","hook":f"Hook {i}","narration":f"Narration {i}","caption":"","hashtags":[],"script_data":{}} for i in range(1,4)]
    with patch("app.api.routes.scripts.generate_variations", return_value=variations):
        script=client.post(f"/api/v1/pages/{page_id}/trends/{rec_id}/generate-scripts").json()
    response=client.post(f"/api/v1/pages/{page_id}/scripts/{script["id"]}/versions",json={"title":"Edited","hook":"New hook","narration":"New narration","caption":"","hashtags":[]})
    assert response.status_code == 201 and response.json()["version_number"] == 4
