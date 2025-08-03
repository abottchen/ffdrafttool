from bs4 import BeautifulSoup

from src.models.player import InjuryStatus
from src.services.web_scraper import FantasySharksScraper


class TestInjuryExtraction:
    def setup_method(self):
        """Set up test fixtures"""
        self.scraper = FantasySharksScraper()

    def test_extract_injury_info_from_img_tag(self):
        """Test extracting injury info from img tag with ONMOUSEOVER"""
        # Create HTML similar to the example provided
        html = """
        <td>
            <a href="#">Aiyuk, Brandon</a>
            <img src="//www.fantasysharks.com/apps/bert//images/injured4.gif"
                 style="vertical-align:middle;"
                 ONMOUSEOVER="popup(&quot;&lt;b&gt; Out&lt;/b&gt; Expected back Preseason Week 2&quot;)"
                 ONMOUSEOUT="removeBox()">
        </td>
        """

        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")

        injury_info = self.scraper._extract_injury_info(cell)

        assert injury_info is not None
        assert injury_info["status"] == InjuryStatus.OUT
        assert "Expected back Preseason Week 2" in injury_info["details"]
        assert injury_info["is_long_term"] is False

    def test_extract_long_term_injury(self):
        """Test extracting long-term injury information"""
        html = """
        <td>
            <a href="#">Player Name</a>
            <img src="//www.fantasysharks.com/apps/bert//images/injured1.gif"
                 ONMOUSEOVER="popup(&quot;&lt;b&gt; Out&lt;/b&gt; Expected back Week 12&quot;)">
        </td>
        """

        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")

        injury_info = self.scraper._extract_injury_info(cell)

        assert injury_info is not None
        assert injury_info["status"] == InjuryStatus.OUT
        assert "Expected back Week 12" in injury_info["details"]
        assert injury_info["is_long_term"] is True

    def test_extract_season_ending_injury(self):
        """Test extracting season-ending injury"""
        html = """
        <td>
            <a href="#">Player Name</a>
            <img src="//www.fantasysharks.com/apps/bert//images/injured2.gif"
                 ONMOUSEOVER="popup(&quot;&lt;b&gt; Out&lt;/b&gt; Out for season with ACL tear&quot;)">
        </td>
        """

        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")

        injury_info = self.scraper._extract_injury_info(cell)

        assert injury_info is not None
        assert injury_info["status"] == InjuryStatus.OUT
        assert "Out for season with ACL tear" in injury_info["details"]
        assert injury_info["is_long_term"] is True

    def test_extract_questionable_injury(self):
        """Test extracting questionable injury status"""
        html = """
        <td>
            <a href="#">Player Name</a>
            <img src="//www.fantasysharks.com/apps/bert//images/injured3.gif"
                 ONMOUSEOVER="popup(&quot;&lt;b&gt; Questionable&lt;/b&gt; Ankle sprain, game-time decision&quot;)">
        </td>
        """

        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")

        injury_info = self.scraper._extract_injury_info(cell)

        assert injury_info is not None
        assert injury_info["status"] == InjuryStatus.QUESTIONABLE
        assert "Ankle sprain, game-time decision" in injury_info["details"]
        assert injury_info["is_long_term"] is False

    def test_no_injury_info(self):
        """Test cell with no injury information"""
        html = """
        <td>
            <a href="#">Healthy Player</a>
        </td>
        """

        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")

        injury_info = self.scraper._extract_injury_info(cell)

        assert injury_info is None

    def test_parse_injury_details_out_status(self):
        """Test parsing various injury detail formats"""
        popup_content = "<b> Out</b> Expected back Week 8"

        injury_details = self.scraper._parse_injury_details(popup_content)

        assert injury_details is not None
        assert injury_details["status"] == InjuryStatus.OUT
        assert injury_details["details"] == "Out Expected back Week 8"
        assert injury_details["is_long_term"] is True

    def test_parse_injury_details_doubtful_status(self):
        """Test parsing doubtful injury status"""
        popup_content = "<b> Doubtful</b> Knee injury, unlikely to play"

        injury_details = self.scraper._parse_injury_details(popup_content)

        assert injury_details is not None
        assert injury_details["status"] == InjuryStatus.DOUBTFUL
        assert injury_details["details"] == "Doubtful Knee injury, unlikely to play"
        assert injury_details["is_long_term"] is False

    def test_parse_injury_details_probable_status(self):
        """Test parsing probable injury status"""
        popup_content = "<b> Probable</b> Minor hamstring, should play"

        injury_details = self.scraper._parse_injury_details(popup_content)

        assert injury_details is not None
        assert injury_details["status"] == InjuryStatus.PROBABLE
        assert injury_details["details"] == "Probable Minor hamstring, should play"
        assert injury_details["is_long_term"] is False
