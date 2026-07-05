from internly.agents.resume_evaluator import evaluate_resume_text


SAMPLE_RESUME_TEXT = """
Priya Sharma
Software engineering student with Python, SQL, data structures, and algorithms experience.
Projects: built a job tracker app and a pathfinding visualizer.
Education: B.Tech Computer Science, 2026.
"""


if __name__ == "__main__":
    profile = evaluate_resume_text(SAMPLE_RESUME_TEXT)
    print(profile.model_dump_json(indent=2))

