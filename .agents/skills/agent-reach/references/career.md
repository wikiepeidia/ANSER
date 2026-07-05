```markdown
# Jobs and Recruiting

LinkedIn.

## LinkedIn

```bash
# Get a personal profile
mcporter call 'linkedin-scraper.get_person_profile(linkedin_url: "https://linkedin.com/in/username")'

# Search for talent
mcporter call 'linkedin-scraper.search_people(keyword: "AI engineer", limit: 10)'

# Get a company profile
mcporter call 'linkedin-scraper.get_company_profile(linkedin_url: "https://linkedin.com/company/xxx")'

# Search for jobs
mcporter call 'linkedin-scraper.search_jobs(keyword: "software engineer", limit: 10)'
```

> **Login required**: the LinkedIn scraper needs a valid authenticated session.

### Fallback Approach

If MCP is unavailable, you can use the Jina Reader:

```bash
curl -s "https://r.jina.ai/https://linkedin.com/in/username"
```
