# DevFolio

DevFolio is a command-line tool that generates professional developer portfolios by leveraging GitHub data and OpenAI's GPT-4 for enhanced content generation.

## Features

- Fetches your GitHub profile and repository data
- Uses AI to generate professional summaries and descriptions
- Creates beautiful portfolios in Markdown format
- Prioritizes your most recently updated repositories
- Secure handling of API keys through environment variables
- Robust error handling and logging

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/TFMV/DevFolio.git
   cd DevFolio
   ```

2. Create a virtual environment and activate it:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:

   ```bash
   cp .env.example .env
   ```

   Then edit the `.env` file with your GitHub and OpenAI API keys.

## Usage

Generate a portfolio for a GitHub user:

```bash
python devfolio.py USERNAME [options]
```

### Options

- `--output` or `-o`: Specify the output file path (without extension)
  - Example: `--output ./portfolios/john_doe`

- `--max-repos` or `-m`: Maximum number of repositories to include (default: 10)

### Examples

Generate a portfolio for a user:

```bash
python devfolio.py octocat
```

Generate a portfolio with a custom output path:

```bash
python devfolio.py octocat --output ./portfolios/octocat_portfolio
```

Limit to 5 repositories:

```bash
python devfolio.py octocat --max-repos 5
```

## Security Considerations

- API keys are stored in a `.env` file which should never be committed to version control
- The `.gitignore` file is configured to exclude the `.env` file
- Error messages are designed to not leak sensitive information
- Input validation is performed to prevent potential security issues
- GitHub API token should use read-only permissions (only `repo:read` scope is needed)

## Performance Optimizations

- Batch processing of OpenAI API calls in small groups to ensure complete responses
- Efficient repository filtering to skip forks without stars
- Sorting repositories by last updated date to highlight recent work
- Caching of API responses to minimize rate limits
- Optimized Markdown generation for better readability
- Uses the latest OpenAI Client API for improved reliability and performance

## Requirements

- Python 3.8 or higher
- GitHub Personal Access Token (with read-only permissions)
- OpenAI API Key

## Technical Details

- Uses the OpenAI Client API (v1.0.0+) for AI-powered content generation
- Implements batch processing to reduce API calls and costs
- Sorts repositories by last updated date to highlight recent work
- Provides enhanced error handling and logging
- Supports customizable output paths

## Example

For an example, see [My Portfolio](TFMV_portfolio.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
