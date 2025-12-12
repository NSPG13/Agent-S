
from typing import List

class Agent:
    def click(
        self,
        element_description: str,
        num_clicks: int = 1,
        button_type: str = "left",
        hold_keys: List = [],
    ):
        print(f"Clicked {element_description} {num_clicks} times with {button_type} button")

agent = Agent()
try:
    agent.click("The Chrome profile tile labeled 'Web'", 1, "left")
    print("SUCCESS: Positional args worked")
except Exception as e:
    print(f"FAILURE: {e}")
