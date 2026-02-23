Feature: viking_curve_login

  Scenario: User logs in and verifies content
    Given I navigate to "https://www.vikingpumpcurve.com/"
    When I log in with username "jraja@idexcorp.com" and password "<data.Password_2>"
    Then I should be on the "https://www.vikingpumpcurve.com/?check_logged_in=1" page
    And I should see the message "Please select operating conditions."