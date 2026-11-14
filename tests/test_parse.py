from tuba_terim_mcp.client import dictionary_ids, parse_search

KUVVET = """
<div id="arama_sonucu_container">
<h2>Toplam Kayıt : <U>2</U></h2>
<div class="title6">Arama Sonucu</div>
<div class="arama_sonucu_content_tumu">
  <div class="sonuc_terim"><b>kuvvet</b> <span class="sozluk_kisa_tanim">(doğa.)</span></div>
  <div>
    <div><i>(Alm. Kraft, f; Fr. force, f; İng. force)</i> <b><i>fiz. </i></b>Cisimlerin ivmelenmesine neden olan nicelik.</div>
    <div class="yorum_link">Yorum ekle</div>
    <div id="yorum_container_282270"></div>
  </div>
</div>
<div class="title6">İlgili Sonuçlar</div>
<div class="arama_sonucu_content_tumu">
  <div class="sonuc_terim" onclick="js_sonuc_tanim(296428)"><b>açısal kuvvet</b> <span class="sozluk_kisa_tanim">(doğa.)</span></div>
  <div class="sonuc_tanim" id="sonuc_tanim_296428">
    <div><i>(Alm. Drehkraft, f; Fr. torque, f; İng. torque)</i> tork.</div>
  </div>
</div>
</div>
<div id="after"></div>
"""

MISS = """
<div id="arama_sonucu_container">
<h2>Toplam Kayıt : <U>0</U></h2>
<div class="title6">Arama Sonucu</div>
<div class="szl_uyari1">Aradığınız terim başlığı sözlük içerisinde bulunmamaktadır.</div>
</div>
<div id="after"></div>
"""

RELATED_ONLY = """
<div id="arama_sonucu_container">
<h2>Toplam Kayıt : <U>2</U></h2>
<div class="title6">Arama Sonucu</div>
<div class="title6">İlgili Sonuçlar</div>
<div class="arama_sonucu_content_tumu">
  <div class="sonuc_terim" onclick="js_sonuc_tanim(1)"><b>özbağlanım</b> <span class="sozluk_kisa_tanim">(müh.)</span></div>
  <div class="sonuc_tanim"><div>Bir seri.</div></div>
</div>
<div class="arama_sonucu_content_tumu">
  <div class="sonuc_terim" onclick="js_sonuc_tanim(2)"><b>özbağlanımlı kayan ortalamalı model</b> <span class="sozluk_kisa_tanim">(müh.)</span></div>
  <div class="sonuc_tanim"><div>ARMA.</div></div>
</div>
</div>
<div id="after"></div>
"""


def test_exact_heading_stays_separate_from_related() -> None:
    result = parse_search(KUVVET, "kuvvet")
    assert result["is_heading"] is True
    assert result["entries"][0]["sozcuk"] == "kuvvet"
    assert result["entries"][0]["ingiliz"] == "force"
    assert result["entries"][0]["sozluk"] == "Doğa Bilimleri Terimleri Sözlüğü"
    assert result["entries"][0]["terim_id"] == "282270"
    assert [item["sozcuk"] for item in result["other_headings"]] == ["açısal kuvvet"]


def test_missing_term_is_not_a_heading() -> None:
    result = parse_search(MISS, "kapalı şık kümesi")
    assert result["is_heading"] is False
    assert result["entries"] == []
    assert result["total"] == 0
    assert "other_headings" not in result


def test_ozbaglanimli_is_not_the_related_heading() -> None:
    result = parse_search(RELATED_ONLY, "özbağlanımlı")
    assert result["is_heading"] is False
    assert result["entries"] == []
    headings = [item["sozcuk"] for item in result["other_headings"]]
    assert "özbağlanımlı" not in headings
    assert "özbağlanımlı kayan ortalamalı model" in headings


def test_dictionary_ids() -> None:
    assert dictionary_ids(None) == "37,38,39"
    assert dictionary_ids("doğa") == "38"
    assert dictionary_ids("Mühendislik Terimleri") == "39"
    assert dictionary_ids("sosyal") == "37"
