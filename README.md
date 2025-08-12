# OpenAQ PM2.5 Sensor Discovery Pipeline

An enterprise-grade data engineering pipeline that discovers and tracks PM2.5 air quality sensors in California using the OpenAQ API and BigQuery.

## 🏗️ Architecture

This pipeline demonstrates modern data engineering practices with:

- **Modular Design**: Separated concerns across focused modules
- **Enterprise Error Handling**: Comprehensive retry logic and graceful failures  
- **Production Monitoring**: Job tracking, metrics collection, and observability
- **Data Quality**: Schema validation, type checking, and data validation
- **Configuration Management**: Environment-aware, easily configurable settings

## 📊 Data Flow

```
OpenAQ API → Data Processing → BigQuery → Analytics/Dashboards
     ↓              ↓              ↓            ↓
  PM2.5 Sensors → Validation → Storage → Insights
```

## 🚀 Key Features

- **Automatic Sensor Discovery**: Finds new PM2.5 sensors in California
- **Intelligent Updates**: Only processes new or changed sensor data
- **Robust API Integration**: Handles rate limiting, retries, and errors
- **Geographic Filtering**: California bounding box filtering
- **Job Monitoring**: Complete pipeline observability and metrics
- **Schema Management**: Automated BigQuery table creation and validation

## 🛠️ Technology Stack

- **Python 3.9+** - Core language
- **OpenAQ API v3** - Air quality data source
- **Google BigQuery** - Data warehouse
- **Pandas** - Data manipulation
- **Google Cloud SDK** - Cloud integration

## 📁 Project Structure

```
openaq_pipeline_project/
├── scripts/
│   ├── sensor_discovery_pipeline.py    # Main pipeline script
│   ├── pipeline_config.py              # Configuration management
│   ├── bigquery_manager.py             # BigQuery operations
│   ├── openaq_client.py                # API client with retry logic
│   ├── sensor_manager.py               # Business logic & data processing
│   ├── job_tracker.py                  # Pipeline monitoring
│   ├── logger.py                       # Logging configuration
│   └── cleanup_data.py                 # Data maintenance utilities
├── logs/                               # Pipeline execution logs
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment variables template
└── README.md                          # This file
```

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.9+
- Google Cloud account with BigQuery enabled
- OpenAQ API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/openaq-pipeline.git
   cd openaq-pipeline
   ```

2. **Create virtual environment**
   ```bash
   python -m venv openaq_env
   openaq_env\Scripts\activate  # Windows
   # source openaq_env/bin/activate  # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   copy .env.example .env
   # Edit .env with your API keys and credentials
   ```

### Environment Variables

Create a `.env` file with:
```
OPENAQ_API_KEY=your_openaq_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=path\to\your\service-account.json
PIPELINE_ENV=production
```

## 🚀 Usage

### Run the Pipeline
```bash
python scripts\sensor_discovery_pipeline.py
```

### Check Table Status
```bash
python scripts\fix_bigquery_schema.py --check
```

### Clean Up Data
```bash
python scripts\cleanup_data.py
```

### Debug API Issues
```bash
python scripts\debug_openaq_data.py --large-sample
```

## 📊 Pipeline Results

The pipeline discovers and tracks:
- **59 PM2.5 sensors** across California
- **Sensor metadata**: Location, ownership, operational status
- **Geographic coverage**: Full California state with lat/lon coordinates
- **Data freshness**: Tracks first and last measurement timestamps

## 🔍 Monitoring & Observability

- **Comprehensive Logging**: All operations logged with timestamps
- **Job Tracking**: Every pipeline run tracked in BigQuery
- **Metrics Collection**: API usage, processing times, data quality
- **Error Handling**: Graceful failures with detailed error reporting

## 📈 Data Schema

### Sensors Table (`pm25_ca_sensors`)
- `sensor_id` (STRING): Unique sensor identifier
- `location_name` (STRING): Human-readable location
- `lat`, `lon` (FLOAT64): Geographic coordinates  
- `datetimeFirst`, `datetimeLast` (TIMESTAMP): Data availability window
- `created_at`, `updated_at` (TIMESTAMP): Pipeline timestamps

### Job Tracking (`job_tracking`)
- `job_id` (STRING): Unique execution identifier
- `status` (STRING): SUCCESS/FAILED/CANCELLED
- `duration_seconds` (FLOAT64): Execution time
- `sensors_processed` (INTEGER): Processing metrics

## 🔧 Development

### Module Testing
Each module can be tested independently:
```bash
python scripts\bigquery_manager.py    # Test BigQuery operations
python scripts\openaq_client.py       # Test API integration  
python scripts\sensor_manager.py      # Test business logic
```

### Adding New Features
The modular architecture makes it easy to extend:
- Add new data sources in `openaq_client.py`
- Extend business logic in `sensor_manager.py`
- Add new metrics in `job_tracker.py`

## 📝 Future Enhancements

- [ ] Hourly measurement data collection
- [ ] Real-time data streaming
- [ ] Looker Studio dashboard integration
- [ ] Automated scheduling with Cloud Functions
- [ ] Multi-state geographic expansion
- [ ] Data quality alerts and monitoring

## 🤝 Contributing

This is a portfolio project demonstrating data engineering best practices. Key principles:
- Clean, modular architecture
- Comprehensive error handling
- Production-ready monitoring
- Professional documentation

## 📄 License

This project is for educational and portfolio purposes.

---

*Built as a demonstration of enterprise-grade data engineering practices*