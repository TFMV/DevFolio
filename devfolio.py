import argparse
import os
import sys
from datetime import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv

from github import Github, GithubException
from openai import OpenAI
from openai import OpenAIError

# ----------------------------
# Configuration & Logging Setup
# ----------------------------
# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("devfolio")

# Get API keys from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate API keys
if not GITHUB_TOKEN:
    logger.error(
        "GitHub token not found. Please set the GITHUB_TOKEN environment variable."
    )
    sys.exit(1)

if not OPENAI_API_KEY:
    logger.error(
        "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
    )
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


# ----------------------------
# GitHub API Integration
# ----------------------------
def fetch_github_profile(username):
    """Fetch GitHub user profile data."""
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user(username)

        # Test if user exists by accessing a property
        _ = user.name

        return {
            "name": user.name or username,
            "bio": user.bio or "No bio available.",
            "avatar_url": user.avatar_url,
            "public_repos": user.public_repos,
            "followers": user.followers,
            "following": user.following,
        }
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        if e.status == 404:
            logger.error(f"User '{username}' not found on GitHub.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error when fetching GitHub profile: {e}")
        sys.exit(1)


def fetch_repositories(username, max_repos=10):
    """Fetch repository details of a GitHub user.

    Args:
        username: GitHub username
        max_repos: Maximum number of repositories to fetch (default: 10)
    """
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user(username)

        repos = []
        # Get all repositories
        all_repos = list(user.get_repos())

        # Sort repositories by last updated date (most recent first)
        all_repos.sort(key=lambda repo: repo.updated_at, reverse=True)
        logger.info("Sorting repositories by last updated date (most recent first)")

        # Process repositories until we have max_repos or run out of repositories
        count = 0
        for repo in all_repos:
            # Skip forks if they don't have any stars
            if repo.fork and repo.stargazers_count == 0:
                continue

            repos.append(
                {
                    "name": repo.name,
                    "description": repo.description or "No description available.",
                    "language": repo.language or "Not specified",
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "last_updated": repo.updated_at.strftime("%Y-%m-%d"),
                    "url": repo.html_url,
                }
            )

            count += 1
            if count >= max_repos:
                break

        if not repos:
            logger.warning(f"No repositories found for user '{username}'.")
        elif len(repos) < max_repos:
            logger.info(
                f"Only found {len(repos)} repositories for user '{username}' after filtering."
            )

        return repos
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error when fetching repositories: {e}")
        sys.exit(1)


# ----------------------------
# AI-Powered Summaries using OpenAI
# ----------------------------
def generate_project_summary(repo):
    """Generate an AI-enhanced summary of a GitHub project."""
    try:
        prompt = f"""
Generate a compelling project description for a portfolio:

- Project: {repo['name']}
- Description: {repo['description']}
- Language: {repo['language']}
- Stars: {repo['stars']}
- Last Updated: {repo['last_updated']}

Write a structured and engaging summary.
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return f"Error generating summary: {e}"
    except Exception as e:
        logger.error(f"Unexpected error when generating project summary: {e}")
        return "Error generating project summary."


def generate_project_summaries(repositories):
    """Batch AI requests for multiple repositories to reduce API calls."""
    if not repositories:
        return []

    try:
        logger.info(
            f"Generating summaries for {len(repositories)} repositories in batches"
        )

        # Process repositories in batches of 5
        BATCH_SIZE = 5
        all_summaries = []

        for i in range(0, len(repositories), BATCH_SIZE):
            batch = repositories[i : i + BATCH_SIZE]
            logger.info(
                f"Processing batch {i//BATCH_SIZE + 1} with {len(batch)} repositories"
            )

            project_prompts = "\n\n".join(
                [
                    f"- Project: {repo['name']}\n- Description: {repo['description']}\n- Language: {repo['language']}\n- Stars: {repo['stars']}\n- Last Updated: {repo['last_updated']}"
                    for repo in batch
                ]
            )

            prompt = f"""Generate professional portfolio summaries for these projects:

{project_prompts}

For each project, write a structured and engaging summary. 
Separate each project summary with three hyphens on a new line (---).
DO NOT include the project name as a header in each summary.
Focus on describing the project's purpose, technologies, and significance."""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1000,  # Increase token limit for multiple responses
            )

            content = response.choices[0].message.content.strip()
            # Split by separator and clean up
            batch_summaries = [summary.strip() for summary in content.split("---")]

            # If we don't have enough summaries for this batch, pad with error messages
            if len(batch_summaries) < len(batch):
                logger.warning(
                    f"Expected {len(batch)} summaries but got {len(batch_summaries)} for batch {i//BATCH_SIZE + 1}"
                )
                batch_summaries.extend(
                    ["Error generating summary"] * (len(batch) - len(batch_summaries))
                )

            # If we have too many summaries for this batch, truncate
            batch_summaries = batch_summaries[: len(batch)]

            # Add batch summaries to all summaries
            all_summaries.extend(batch_summaries)

        return all_summaries
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return ["Error generating summary"] * len(repositories)
    except Exception as e:
        logger.error(f"Unexpected error when generating project summaries: {e}")
        return ["Error generating project summary"] * len(repositories)


def generate_professional_bio(profile):
    """Generate an AI-powered professional bio using GitHub profile data."""
    try:
        prompt = f"""
Generate a professional bio for a software developer:

- Name: {profile['name']}
- Bio: {profile['bio']}
- Public Repositories: {profile['public_repos']}
- Followers: {profile['followers']}

Make it concise, engaging, and ideal for a portfolio website.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return f"Error generating bio: {e}"
    except Exception as e:
        logger.error(f"Unexpected error when generating professional bio: {e}")
        return "Error generating professional bio."


# ----------------------------
# Portfolio Export Options
# ----------------------------
def generate_markdown(profile, projects, output_path=None):
    """Convert AI-generated content into Markdown format.

    Args:
        profile: GitHub profile data
        projects: List of repository data
        output_path: Path to save the markdown file (default: portfolio.md)
    """
    try:
        # Generate professional bio using AI
        professional_bio = generate_professional_bio(profile)

        # Generate summaries for all projects in batch
        summaries = generate_project_summaries(projects)

        markdown_content = f"# {profile['name']}'s Portfolio\n\n"
        markdown_content += f"![Profile Picture]({profile['avatar_url']})\n\n"
        markdown_content += f"**Bio:** {professional_bio}\n\n"
        markdown_content += "## Projects\n\n"

        for i, project in enumerate(projects):
            summary = summaries[i] if i < len(summaries) else "Error generating summary"

            # Clean up the summary by removing the project name header
            # This removes lines like "# ProjectName" from the beginning of summaries
            summary_lines = summary.split("\n")
            if summary_lines and (
                summary_lines[0].startswith("# ") or summary_lines[0].startswith("#")
            ):
                summary = "\n".join(summary_lines[1:]).strip()

            markdown_content += f"### [{project['name']}]({project['url']}) ⭐ {project['stars']} | 🍴 {project['forks']}\n"
            markdown_content += f"**Description:** {project['description']}\n\n"
            markdown_content += f"**Summary:** {summary}\n\n"
            markdown_content += f"**Language:** `{project['language']}` | **Last Updated:** _{project['last_updated']}_\n\n"

        output_file = output_path or "portfolio.md"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(markdown_content)
        logger.info(f"Markdown portfolio generated: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error generating markdown: {e}")
        sys.exit(1)


# ----------------------------
# Main Execution Logic
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="DevFolio Portfolio Generator")
    parser.add_argument("username", help="GitHub username to fetch data for")
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (without extension)",
    )
    parser.add_argument(
        "--max-repos",
        "-m",
        type=int,
        default=10,
        help="Maximum number of repositories to include (default: 10)",
    )
    args = parser.parse_args()

    # Set default output filename based on username if not provided
    if not args.output:
        args.output = f"{args.username}_portfolio"
        logger.info(f"No output path specified, using default: {args.output}")

    # Create output directory if it doesn't exist
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

    # Fetch data from GitHub
    logger.info(f"Fetching GitHub profile for user: {args.username}")
    profile = fetch_github_profile(args.username)

    logger.info(
        f"Fetching repositories for user: {args.username} (max: {args.max_repos})"
    )
    repos = fetch_repositories(args.username, args.max_repos)

    # Generate markdown output
    md_output = f"{args.output}.md" if args.output else None
    generate_markdown(profile, repos, md_output)

    logger.info("Portfolio generation completed successfully!")


if __name__ == "__main__":
    main()
