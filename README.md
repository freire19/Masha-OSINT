# 🕵️‍♀️ Masha OSINT v3.0

**Full Spectrum Intelligence Platform** - Autonomous OSINT investigation system combining DeepSeek AI, SerpAPI, Web Crawler, Sherlock (474 social platforms), and WHOIS lookup.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Features

### 🤖 AI-Powered Investigation
- **DeepSeek Reasoner** generates advanced Google dorks and analyzes findings
- **Automated Planning** creates investigation strategy for each target
- **Confidence Scoring** rates each finding's reliability
- **Multi-Source Correlation** combines data from multiple OSINT sources

### 🔍 Intelligence Sources
- **Google Search** via SerpAPI (organic + news results)
- **Social Media** enumeration across 474 platforms (Sherlock integration)
- **Web Crawler** with WAF bypass (curl_cffi with Chrome 110 TLS fingerprint)
- **WHOIS Lookup** for domain intelligence
- **BreachDirectory** for leaked credentials (optional)

### 🎯 Target Types Supported
- **Email addresses** (john@example.com)
- **Person names** (John Doe, "Jane Smith")
- **Domains** (example.com, www.example.com)
- **Phone numbers** (Brazilian and international formats)
- **CPF** (Brazilian individual tax ID)
- **CNPJ** (Brazilian company tax ID)
- **Usernames** (social media handles)

### 🖥️ Dual Interface
- **Streamlit Web UI** - User-friendly web interface with dark theme
- **CLI Tool** - Command-line interface for automation and scripting

### 📊 Investigation Pipeline
1. **Phase 1 (Planning)**: DeepSeek generates targeted search queries
2. **Phase 2 (Scanning)**: Execute searches across all sources
3. **Phase 3 (Infiltration)**: Deep crawl of discovered URLs
4. **Phase 4 (Analysis)**: AI generates comprehensive intelligence dossier

---

## Quick Start

### Prerequisites
- Python 3.10+ (3.12+ recommended)
- Git
- 2GB RAM minimum
- API Keys:
  - [DeepSeek API Key](https://platform.deepseek.com) (required)
  - [SerpAPI Key](https://serpapi.com) (required)
  - [RapidAPI Key](https://rapidapi.com) (optional, for leak checks)

### Installation

```bash
# Clone repository
git clone https://github.com/freire19/Masha-OSINT.git
cd Masha-OSINT

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API keys
```

### Configuration

Edit [.env](.env) file with your API keys:

```bash
# REQUIRED
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
SERPAPI_KEY=your-serpapi-key

# OPTIONAL
MASHA_WEB_PASSWORD=your-web-password
RAPIDAPI_KEY=your-rapidapi-key
DEEPSEEK_MODEL=deepseek-reasoner
```

### Running the Application

#### Web UI (Streamlit)

```bash
# Start web interface
streamlit run app.py

# Or use make
make run-web
```

Access at: http://localhost:8501

#### CLI Tool

```bash
# Basic investigation
python main.py -t "target@email.com"

# JSON output only (for automation)
python main.py -t "johndoe" --json-output

# Custom output file
python main.py -t "example.com" -o investigation.json
```

### Verify Installation

```bash
python health_check.py
```

Expected output: "✅ SISTEMA PRONTO PARA USO"

---

## Usage Examples

### Web UI

1. Open http://localhost:8501
2. Enter password (from .env)
3. Select operation mode:
   - **Investigação Completa** - Full AI-powered investigation
   - **Apenas Busca** - Search only (no AI analysis)
   - **Apenas Crawler** - Web crawler only
4. Enter target and click "Investigar"

### CLI Tool

```bash
# Email investigation
python main.py -t "john.doe@company.com"

# Domain investigation
python main.py -t "example.com"

# Username investigation (social media)
python main.py -t "johndoe123"

# Brazilian CPF investigation
python main.py -t "123.456.789-00"

# Brazilian phone investigation
python main.py -t "+55 11 98765-4321"

# JSON-only output (no console logs)
python main.py -t "target" --json-output > result.json
```

### Makefile Commands

```bash
make install        # Install dependencies
make test           # Run test suite
make health         # Health check
make run-web        # Start Streamlit web UI
make run-cli        # Run CLI tool (interactive)
make docs           # Generate documentation
make security       # Run security checks
make clean          # Clean temp files
```

---

## Production Deployment

For production deployment to a VPS with domain and SSL, see the comprehensive deployment guide:

**[📖 Deployment Guide](docs/DEPLOYMENT.md)**

Covers:
- VPS security hardening (firewall, Fail2Ban)
- Systemd service configuration
- Nginx reverse proxy setup
- SSL certificate with Let's Encrypt
- Monitoring and backup automation
- Troubleshooting guide

---

## Project Structure

```
Masha-OSINT/
├── app.py                  # Streamlit web UI
├── main.py                 # CLI tool
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── health_check.py        # System health check
├── Makefile               # Development tasks
├── src/
│   ├── agents/
│   │   └── brain.py       # DeepSeek AI agent
│   ├── tools/
│   │   ├── web_search.py  # SerpAPI integration
│   │   ├── web_crawler.py # Web crawling
│   │   ├── username_check.py  # Sherlock integration
│   │   ├── whois_lookup.py    # WHOIS queries
│   │   └── leak_check.py      # BreachDirectory
│   ├── utils/
│   │   ├── detect_target_type.py  # Target classifier
│   │   ├── logger.py      # Logging system
│   │   └── monitoring.py  # Performance monitoring
│   └── config/
│       └── masha_config.py  # Configuration
├── docs/
│   ├── DEPLOYMENT.md      # Production deployment
│   └── ...                # Additional documentation
└── tests/
    └── ...                # Test suite
```

---

## System Requirements

### Development
- Python 3.10+ (3.12+ recommended)
- 2GB RAM minimum
- 1GB disk space
- Internet connection (for API calls)

### Production
- Ubuntu 22.04+ or Debian 11+
- 4GB RAM recommended
- 2GB+ disk space (for logs)
- Nginx (reverse proxy)
- Certbot (SSL certificates)

---

## Security

### ⚠️ Critical Security Notes

1. **NEVER commit .env** - Contains sensitive API keys
2. **Change default password** - Update `MASHA_WEB_PASSWORD` before deployment
3. **Use HTTPS in production** - See deployment guide for SSL setup
4. **Secure .env permissions** - `chmod 600 .env`
5. **Monitor API usage** - SerpAPI and DeepSeek have rate limits
6. **Run as non-root** - Use dedicated user in production

### API Key Security

Your [.env](.env) file contains sensitive credentials:
- ✅ **Already in .gitignore** - Won't be committed to git
- ✅ **Local only** - Never share or upload
- ✅ **Environment variables** - Loaded at runtime

### Web UI Authentication

The Streamlit web UI requires password authentication (configured via `MASHA_WEB_PASSWORD` in .env).

**Default password in .env.example:** Change this immediately!

---

## Monitoring & Logs

### Log Files

Investigations are saved in [logs/](logs/):
- `logs/Masha_{target}_FULL.json` - Complete investigation results
- `logs/structured/` - Structured metrics (optional)
- `logs/investigations/` - Investigation history

### Health Check

```bash
python health_check.py
```

Verifies:
- Environment variables
- Python dependencies
- API connectivity
- System resources

### Performance Monitoring

The application tracks:
- API response times
- Success/failure rates
- Resource usage (CPU, memory)
- Investigation duration

---

## Development

### Running Tests

```bash
# Run test suite
pytest

# With coverage
pytest --cov=src tests/

# Specific test file
pytest tests/test_brain.py
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 src/

# Type checking
mypy src/
```

### Documentation

```bash
# Generate docs
mkdocs build

# Serve locally
mkdocs serve
# Access at: http://127.0.0.1:8000
```

---

## API Usage & Costs

### DeepSeek API
- **Pricing**: ~$0.27/1M input tokens, ~$1.10/1M output tokens
- **Model**: deepseek-reasoner (default)
- **Usage**: Investigation planning + analysis
- **Estimate**: ~$0.01-0.05 per investigation

### SerpAPI
- **Pricing**: ~$0.003 per search
- **Quota**: 100 searches/month (free tier)
- **Usage**: Google search results
- **Estimate**: 5-10 searches per investigation

### RapidAPI (BreachDirectory)
- **Pricing**: Variable by plan
- **Optional**: Not required for core functionality
- **Usage**: Email leak checking

**Total cost per investigation**: ~$0.01-0.10 (depending on search depth)

---

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt --upgrade
```

#### 2. API Key Errors
```bash
# Verify .env configuration
cat .env | grep -E "(DEEPSEEK|SERPAPI)"

# Check environment variables are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DEEPSEEK_API_KEY' in os.environ)"
```

#### 3. Streamlit Connection Errors
```bash
# Kill existing Streamlit processes
pkill -f streamlit

# Restart
streamlit run app.py
```

#### 4. Permission Denied
```bash
# Fix .env permissions
chmod 600 .env

# Fix log directory permissions
chmod 755 logs/
```

### Debug Mode

Enable verbose logging:

```bash
# Set in .env or environment
export MASHA_DEBUG=true

# Run with debug output
python main.py -t "target" --verbose
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Keep commits atomic and descriptive

---

## Roadmap

### Planned Features
- [ ] Local CNPJ database integration
- [ ] Additional OSINT sources (LinkedIn, Twitter API)
- [ ] Advanced reporting (PDF export)
- [ ] Multi-language support
- [ ] API endpoint for integrations
- [ ] Docker deployment support
- [ ] Rate limiting and queueing

### Version History

**v3.0 (Current)**
- AI-powered investigation planning
- Hybrid CLI + Web interface
- Sherlock integration (474 platforms)
- Enhanced web crawler with WAF bypass

**v2.0**
- Added Streamlit web UI
- SerpAPI integration
- Basic AI analysis

**v1.0**
- Initial CLI tool
- Manual search and crawling

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Disclaimer

**⚠️ Legal Notice:**

This tool is provided for **educational and authorized security testing purposes only**.

- ✅ **Authorized use**: Penetration testing, security research, CTF competitions
- ❌ **Prohibited use**: Unauthorized access, stalking, harassment, illegal activities

**By using this tool, you agree to:**
1. Comply with all applicable laws and regulations
2. Only target systems you have permission to test
3. Respect privacy and data protection laws
4. Take responsibility for your actions

**The authors are not responsible for misuse of this tool.**

---

## Acknowledgments

- **DeepSeek AI** - Advanced reasoning model
- **SerpAPI** - Google Search API
- **Sherlock Project** - Username search across platforms
- **curl_cffi** - Stealth HTTP client
- **Streamlit** - Web UI framework

---

## Support & Contact

- **GitHub**: [@freire19](https://github.com/freire19)
- **Issues**: [GitHub Issues](https://github.com/freire19/Masha-OSINT/issues)
- **Documentation**: [docs/](docs/)

---

## Star History

If you find this project useful, please consider giving it a ⭐ on GitHub!

---

**Made with 🖤 by freire19**
