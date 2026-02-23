Feature: RecordedSession
  Scenario: User explores the PupilLeader website and verifies key content

    Given Navigate to "https://pupilleader.com/"
    When Click on the element containing the text "A leading communication platform to connect school"
    Then I should see the heading with text "A leading communication platform to connect school, Teachers and parents"
    When Click on the "About Us" link
    Then I should be on the "https://pupilleader.com/about.html" page
    And I should see the heading with text "Best School Management Software with Communication Platform across Schools"