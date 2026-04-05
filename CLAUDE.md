# CLAUDE.md - AI Assistant Guide for Keiba_Shisaku20250928

## Project Overview

**Repository**: Keiba_Shisaku20250928 (競馬試作 - Horse Racing Prediction Study)
**Purpose**: Japanese horse racing analysis and prediction system using machine learning
**Primary Language**: Python with Japanese comments and UI
**Architecture**: Monolithic GUI application with integrated data collection, ML training, and prediction

This is a sophisticated horse racing prediction system that:
- Scrapes historical race data from netkeiba.com
- Engineers 35+ features from horse career histories
- Trains ensemble ML models (LightGBM + Logistic Regression)
- Performs Monte Carlo simulations for exotic bet probabilities
- Recommends bets using Kelly criterion based on expected value

## Repository Structure

```
/home/user/Keiba_Shisaku20250928/
├── horse_racing_analyzer.py    # Main application (5,412 lines)
├── collect_data.py.txt         # Standalone data collection module (766 lines)
├── settings.json               # Configuration file
├── calibration_plot.png        # Visualization output
├── README.md                   # Basic project metadata
└── .git/                       # Git repository
```

### Key Files

#### 1. `horse_racing_analyzer.py` (PRIMARY APPLICATION)
- **Purpose**: Complete GUI application for horse racing prediction
- **Architecture**: Single class `HorseRacingAnalyzerApp` with 6 tabbed UI sections
- **LOC**: 5,412 lines
- **Dependencies**: tkinter, pandas, numpy, lightgbm, sklearn, selenium, beautifulsoup4

**Core Components**:
- Data collection (web scraping)
- Feature engineering (35+ features)
- ML model training (ensemble approach)
- Real-time prediction
- Monte Carlo simulation
- Result validation

#### 2. `collect_data.py.txt`
- **Purpose**: Reusable data scraper for netkeiba.com
- **Can be used**: Independently for batch data collection
- **Key Functions**: `get_kaisai_dates()`, `get_race_ids()`, `get_result_table()`, `get_pay_table()`

#### 3. `settings.json`
Configuration parameters for the application:
```json
{
    "data_directory": "C:\\Users\\bu158\\試作\\data",
    "model_directory": "C:\\Users\\bu158\\試作\\models",
    "min_odds": 1.5,
    "max_odds": 50.0,
    "min_expected_value": 1.0,
    "kelly_fraction": 0.1
}
```

## Code Architecture

### Main Class: `HorseRacingAnalyzerApp`

**Initialization** (`__init__` at line 87):
- Sets up Tkinter GUI with 6 tabs
- Loads settings, cache, and models
- Initializes data structures (DataFrames, dictionaries)
- Configures matplotlib for Japanese fonts

**Key Attributes**:
```python
self.combined_data         # Merged race/horse/result data (DataFrame)
self.processed_data        # Feature-engineered dataset for ML (DataFrame)
self.horse_details_cache   # Horse career data cache (dict)
self.trained_model         # LightGBM model
self.model_features        # Feature names used in training (list)
self.imputation_values_    # Missing value defaults (dict)
```

**Data Structures**:
- JRA track list: `JRA_TRACKS` (line 85)
- Various statistics caches: `course_time_stats`, `father_stats`, `mother_father_stats`, `gate_stats`, `reference_times`

### Feature Engineering Pipeline

**Master Function**: `calculate_original_index()` (line 1069)

**35+ Features Calculated**:

1. **Basic Information** (4):
   - Age, Sex, Load (weight), 枠番 (gate number)

2. **Recent Performance** (6):
   - JRA-only: `jra_近走1走前着順`, `jra_近走2走前着順`, `jra_近走3走前着順`
   - All races: `全_近走1走前着順`, `全_近走2走前着順`, `全_近走3走前着順`

3. **Weight Metrics** (5):
   - `斤量絶対値` (absolute load), `斤量前走差` (load change)
   - `馬体重絶対値` (horse weight), `馬体重前走差` (weight change)
   - `負担率` (load ratio)

4. **Performance Metrics** (3):
   - `タイム偏差値` (time deviation score)
   - `同コース距離最速補正` (course-specific time adjustment)
   - `上がり3F_1走前` (last 3F time)

5. **Pedigree Analysis** (2):
   - `父同条件複勝率` (sire same-condition place rate)
   - `母父同条件複勝率` (dam-sire same-condition place rate)

6. **Statistical Rates** (3):
   - `枠番_複勝率` (gate position place rate)
   - `騎手コース複勝率` (jockey-course partnership rate)
   - `馬コース複勝率` (horse-course partnership rate)

7. **Race Context** (4):
   - `距離区分` (distance category: sprint/mile/intermediate/long)
   - `race_class_level` (race class level)
   - `days_since_last_race`
   - Market data: `OddsShutuba`, `NinkiShutuba`

8. **Running Style** (9):
   - `leg_type` (0=逃げ, 1=先行, 2=差し, 3=追込, 4=unknown)
   - `avg_4c_position` (average corner position)
   - `hana_shucho_score` (front-running intensity)
   - Race composition: `num_nige_horses`, `num_senko_horses`, `num_sashi_horses`, `num_oikomi_horses`
   - `num_high_hana_shucho` (number of strong front-runners)

9. **Rankings & Advanced** (5):
   - `time_dev_rank`, `last3f_rank`
   - `avg_member_time_dev`, `avg_member_last3f`
   - Race quality indicators

10. **Transfer & History** (3):
    - `is_transfer` (whether horse transferred regions)
    - `num_jra_starts` (JRA race count)
    - `jra_rank_1ago` (last JRA race ranking)

**Feature Engineering Pattern**:
```python
# Calculate features avoiding data leakage
features = {
    'Age': np.nan,
    'Sex': np.nan,
    # ... initialize all 35+ features
}

# Extract from horse_details (career history)
jra_results = horse_details.get('jra_race_results', [])
all_results = horse_details.get('race_results', [])

# Calculate statistics from historical data
# IMPORTANT: Always exclude current race to prevent leakage!
```

### Machine Learning Pipeline

**Training Function**: `train_and_evaluate_model()` (line 2239)

**Ensemble Approach**:
1. **LightGBM Classifier**
   - Gradient boosting for strong predictions
   - Parameters: 1000 trees, early stopping

2. **Logistic Regression**
   - Balanced feature evaluation
   - StandardScaler preprocessing

3. **Isotonic Regression**
   - Probability calibration for reliability

**Training Process**:
```python
# 1. Train/test split (80/20)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 2. Train LightGBM
lgb_model = lgb.LGBMClassifier(n_estimators=1000)
lgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=50)

# 3. Train Logistic Regression
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
lr_model = LogisticRegression()
lr_model.fit(X_train_scaled, y_train)

# 4. Calibrate probabilities
calibrator = IsotonicRegression(out_of_bounds='clip')
calibrator.fit(lgb_pred_proba, y_test)

# 5. Ensemble prediction: (LightGBM + LR) / 2
```

**Model Files Saved** (6 per mode: win/place):
- `trained_lgbm_model_{mode}.pkl` - LightGBM model
- `lr_model_{mode}.pkl` - Logistic regression model
- `scaler_{mode}.pkl` - StandardScaler
- `calibrator_{mode}.pkl` - IsotonicRegression calibrator
- `model_features_{mode}.pkl` - Feature names list
- `imputation_values_{mode}.pkl` - Missing value defaults

### Prediction Pipeline

**Real-time Prediction Flow**:
```
User Input: Race ID (12-digit netkeiba race ID)
    ↓
get_shutuba_table(race_id) → Current race entry list
    ↓
For each horse:
    get_horse_details(horse_id) → Career history (cached)
    ↓
    calculate_original_index() → 35+ features
    ↓
Load ensemble models (6 files)
    ↓
Predict probabilities:
    - LGBM prediction → Calibration → p1
    - LR prediction (scaled) → p2
    - Final: (p1 + p2) / 2
    ↓
Monte Carlo Simulation (10,000 iterations):
    - Sample race outcomes using probabilities
    - Calculate exotic bet frequencies
    ↓
Kelly Criterion Betting:
    - EV = P(win) × Odds - 1
    - Filter by min_odds, max_odds, min_EV
    - Bet size = Kelly_fraction × (P×Odds - 1) / (Odds - 1)
    ↓
Display recommendations
```

## Data Sources and Formats

### Web Scraping (netkeiba.com)

**Selenium Usage**:
- Chrome WebDriver required
- Configurable in settings: `chrome_driver_path`
- Wait timeouts: `SELENIUM_WAIT_TIMEOUT = 30s`

**Key URLs**:
- Calendar: `https://race.netkeiba.com/top/calendar.html?year={year}&month={month}`
- Race list: `https://race.netkeiba.com/top/race_list.html?kaisai_date={YYYYMMDD}`
- Race details: `https://race.netkeiba.com/race/shutuba.html?race_id={race_id}`
- Horse details: `https://db.netkeiba.com/horse/{horse_id}/`

**Rate Limiting**:
```python
SLEEP_TIME_PER_PAGE = 0.7  # seconds between page requests
SLEEP_TIME_PER_RACE = 0.2  # seconds between race requests
```

### Data Persistence

**Cache Files** (pickle format):
- `horse_details_cache.pkl` - Horse career histories
- Loaded on startup: `load_cache_from_file()`
- Saved on exit: `save_cache_to_file()`

**CSV/JSON Support**:
- Import race results: CSV format
- Import payout data: JSON format
- Export predictions: CSV format

## Development Workflows

### Common Development Tasks

#### 1. Adding New Features

**Location**: `calculate_original_index()` method (line 1069)

**Steps**:
1. Add feature name to `features` dict initialization
2. Calculate feature value from `horse_details` or `race_conditions`
3. **CRITICAL**: Ensure no data leakage (exclude current race data)
4. Update `leak_free_features` list in `train_and_evaluate_model()` (line 2268)
5. Retrain models with new features

**Example**:
```python
def calculate_original_index(self, horse_details, race_conditions, race_members_df=None):
    features = {
        # ... existing features ...
        'new_feature_name': np.nan,  # 1. Initialize
    }

    # ... existing code ...

    # 2. Calculate new feature
    past_races = horse_details.get('race_results', [])
    if len(past_races) > 0:
        features['new_feature_name'] = some_calculation(past_races)
```

#### 2. Modifying Model Architecture

**Location**: `train_and_evaluate_model()` method (line 2239)

**Ensemble Components**:
- LightGBM parameters around line 2300
- Logistic Regression around line 2350
- Calibration around line 2400

**Testing Changes**:
1. Use "データ管理" tab → "モデルを学習" button
2. Monitor training output in console
3. Check calibration plot: `calibration_plot.png`
4. Validate with "結果検証" tab

#### 3. Adjusting Scraping Logic

**Location**: Data collection methods (lines 3500-4500 approx)

**Key Methods**:
- `get_kaisai_dates()` - Calendar scraping
- `get_race_ids()` - Race list extraction
- `get_shutuba_table()` - Entry data
- `get_result_table()` - Race results
- `get_horse_details()` - Career history

**Error Handling Pattern**:
```python
try:
    response = requests.get(url, timeout=self.REQUEST_TIMEOUT, headers=headers)
    response.raise_for_status()
    # ... parse data ...
except requests.exceptions.RequestException as e:
    print(f"ERROR: Request failed for {url}. Error: {e}")
    return None
```

#### 4. UI Modifications

**Location**: Tab creation methods (lines 87-200)

**6 Tabs**:
- `self.tab_home` - Home/quick start
- `self.tab_data` - Data management
- `self.tab_analysis` - Statistical analysis
- `self.tab_prediction` - Prediction interface
- `self.tab_results` - Result validation
- `self.tab_settings` - Settings editor

**UI Update Pattern**:
```python
# Always use root.after() for thread-safe GUI updates
self.root.after(0, lambda: self.update_status("Status message"))
self.root.after(0, lambda: messagebox.showinfo("Title", "Message"))
```

### Testing and Validation

#### Running the Application
```bash
python horse_racing_analyzer.py
```

#### Validation Workflow
1. **Collect Data**: Use "データ管理" tab
   - Fetch race data for specific dates
   - Verify horse_details_cache builds correctly

2. **Train Models**: "データ管理" → "モデルを学習"
   - Monitor console for ROC-AUC scores
   - Check for feature importance warnings

3. **Backtest**: "結果検証" tab
   - Input past race IDs
   - Compare predictions vs actual results
   - Calculate hit rates and profit/loss

4. **Live Prediction**: "予測" tab
   - Input upcoming race ID
   - Review probability distributions
   - Check Kelly criterion recommendations

## Code Conventions and Patterns

### Japanese Language Usage
- **Comments**: Mix of Japanese and English
- **Variable Names**: English or romaji
- **UI Labels**: Japanese (Tkinter ttk widgets)
- **Print Statements**: Japanese for user messages

### Naming Conventions
- **Methods**: snake_case (e.g., `calculate_original_index()`)
- **Class**: PascalCase (e.g., `HorseRacingAnalyzerApp`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `JRA_TRACKS`)
- **GUI widgets**: descriptive names (e.g., `self.tab_prediction`)

### Error Handling
```python
# Standard pattern for data processing
try:
    # ... processing logic ...
except Exception as e:
    print(f"ERROR: {context}. Error: {e}")
    traceback.print_exc()
    return None  # or appropriate default
```

### Threading Pattern
```python
# For long-running operations
def _some_operation_thread(self):
    """Background thread for time-consuming task"""
    try:
        # ... do work ...
        self.root.after(0, lambda: self.update_status("Complete"))
    except Exception as e:
        self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

# Start thread
thread = threading.Thread(target=self._some_operation_thread, daemon=True)
thread.start()
```

### Pickle Operations
```python
# Standardized pickle load/save helpers
data = self._load_pickle(file_path)  # Returns None on failure
success = self._save_pickle(data, file_path)  # Returns bool
```

### Data Leakage Prevention
**CRITICAL PATTERN**: Always exclude current race when calculating statistics
```python
# CORRECT: Filter out current race
past_races = [r for r in race_results if r['date'] < current_race_date]

# WRONG: Using all races (includes future data)
all_races = race_results  # This causes data leakage!
```

## Known Issues and Current State

### Active Issues (from git history)
1. **Feature Underutilization** (Nov 2024)
   - Not all 35+ features being used in predictions
   - Check feature importance in LightGBM output

2. **Low-Popularity Bias** (Nov 2024)
   - Model recommending too many outsiders (low-popularity horses)
   - May need probability calibration adjustment

3. **Feature Selection** (Oct 2024)
   - Features not properly reflected in model training
   - Verify `leak_free_features` list matches actual features

### Debugging Tips

**Check Feature Usage**:
```python
# After training, inspect feature importance
print(f"Features used: {len(self.model_features)}")
print(f"LGBM feature importance: {lgb_model.feature_importances_}")
```

**Verify Data Leakage Prevention**:
```python
# In calculate_original_index(), confirm past_races filter
print(f"Total races: {len(all_results)}, Past races: {len(past_races)}")
```

**Monitor Predictions**:
```python
# In prediction pipeline, log probabilities
print(f"Horse {horse_name}: Win={win_prob:.3f}, Place={place_prob:.3f}")
```

## Configuration and Settings

### settings.json Parameters

**Required**:
- `data_directory` - Where to store data files
- `model_directory` - Where to save trained models

**Betting Filters**:
- `min_odds` (default: 1.5) - Minimum odds to consider
- `max_odds` (default: 50.0) - Maximum odds to consider
- `min_expected_value` (default: 1.0) - Minimum EV threshold

**Kelly Criterion**:
- `kelly_fraction` (default: 0.1) - Fraction of Kelly bet size (10% = conservative)

**Optional Advanced**:
- `scrape_sleep_page` - Seconds between page requests
- `scrape_sleep_race` - Seconds between race requests
- `chrome_driver_path` - Path to ChromeDriver
- `user_agent` - Custom user agent string

### Font Configuration
**Location**: Lines 28-39 in `horse_racing_analyzer.py`

For Windows: Uses Meiryo font by default
For Linux: May need to install Japanese fonts and update:
```python
plt.rcParams['font.family'] = 'TakaoPGothic'  # or other Japanese font
```

## Git Workflow Requirements

### Branch Requirements
- **Development Branch**: `claude/claude-md-mhy4thbfwdxgq2qg-01KutTrZc8Wvkfe5BbKgahMa`
- **CRITICAL**: All pushes must go to branches starting with `claude/` and ending with session ID
- **Main Branch**: (not specified, likely `main` or `master`)

### Git Operations
**Push with retry**:
```bash
git push -u origin claude/claude-md-mhy4thbfwdxgq2qg-01KutTrZc8Wvkfe5BbKgahMa
# If network error, retry up to 4 times with exponential backoff
```

**Commit Message Style** (from git log):
- Japanese language
- Descriptive of changes
- Examples: "人気薄推奨対策中", "特徴量が全部使われていない状況"

## Dependencies and Requirements

### Python Version
- Python 3.7+ recommended (uses type hints)

### Core Dependencies
```
pandas
numpy
lightgbm
scikit-learn
matplotlib
tkinter (standard library)
```

### Web Scraping
```
selenium
beautifulsoup4
requests
lxml
```

### Installation
```bash
pip install pandas numpy lightgbm scikit-learn matplotlib selenium beautifulsoup4 requests lxml
```

**ChromeDriver**: Required for Selenium
- Download from: https://chromedriver.chromium.org/
- Place in PATH or specify in settings.json

## AI Assistant Guidelines

### When Making Changes

1. **Always Read First**: Use Read tool on relevant sections before editing
2. **Preserve Japanese**: Keep Japanese comments and UI text
3. **Test Locally**: Changes to ML pipeline require retraining models
4. **Avoid Data Leakage**: Critical in any feature engineering changes
5. **Update Feature Lists**: When adding features, update ALL relevant locations:
   - Feature dict initialization in `calculate_original_index()`
   - `leak_free_features` list in `train_and_evaluate_model()`
   - Any validation/display logic

### When Debugging

1. **Check Console Output**: Application logs extensively to stdout
2. **Inspect Cache**: `horse_details_cache.pkl` may be corrupted if errors occur
3. **Verify Model Files**: All 6 model files must exist for predictions
4. **Review Feature Engineering**: Most bugs are in `calculate_original_index()`

### When Adding Features

1. **Understand Context**: Read horse racing domain knowledge if needed
2. **Avoid Leakage**: Never use future race data in features
3. **Handle Missing Data**: Initialize with np.nan, handle in model training
4. **Document Purpose**: Add Japanese comment explaining new feature
5. **Test Impact**: Retrain and evaluate before/after adding feature

### Best Practices

- **Incremental Changes**: This is a 5,000+ line monolithic app; make small changes
- **Preserve Structure**: Don't refactor architecture without explicit request
- **Respect Threading**: GUI updates must use `self.root.after(0, lambda: ...)`
- **Cache Awareness**: Horse details cache saves hours of scraping time
- **Model Compatibility**: Changing features requires retraining ALL models

## Quick Reference

### Key Line Numbers
- Class initialization: Line 87
- Feature engineering: Line 1069
- Model training: Line 2239
- Data collection methods: Lines 3500-4500
- JRA track list: Line 85
- Settings loading: Lines 166-189

### Common Race ID Format
- 12 digits: `YYYYMMDD{track_code}{race_num}{round}`
- Example: `202411031001` = 2024-11-03, track 10, race 01

### Quick Commands
```bash
# Run application
python horse_racing_analyzer.py

# Check git status
git status

# View recent logs
git log --oneline -10
```

---

**Last Updated**: 2025-11-14
**Application Version**: Active development (Nov 2024 commits)
**Status**: Production-ready with ongoing refinements to feature engineering and prediction accuracy
