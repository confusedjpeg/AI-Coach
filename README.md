# 🎓 AI-Powered Adaptive Learning System

A comprehensive learning management system powered by 4 specialized AI agents that create personalized learning experiences, analyze study sessions, optimize schedules, and provide adaptive recommendations.

## 🌟 Features Overview

### 🤖 Four Specialized AI Agents

#### 1. **Learning Path Creator Agent**
- Creates personalized learning curricula based on your goals and preferences
- Adapts difficulty levels and pacing to your learning style
- Generates structured topic progressions with detailed descriptions
- Considers time constraints and availability

#### 2. **Study Session Analyzer Agent**
- Analyzes every study session for effectiveness and learning outcomes
- Tracks mood, productivity, and session duration
- Automatically marks topics as completed based on performance
- Provides detailed insights and recommendations for improvement

#### 3. **Schedule Optimizer Agent**
- Creates optimal study schedules based on your availability
- Considers preferred learning times (morning, afternoon, evening)
- Balances topics across time periods for maximum retention
- Adapts to weekly time commitments and learning goals

#### 4. **Adaptive Agent**
- Continuously analyzes your learning patterns and progress
- Provides real-time recommendations for learning adjustments
- Suggests next topics to focus on based on performance
- Optimizes learning strategies based on data-driven insights

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- PostgreSQL database

### Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd Agents
    ```

2.  **Create virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**
    Create a `.env` file in the root directory:
    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    DATABASE_URL=postgresql://username:password@localhost:5432/learning_db
    ```

5.  **Set up the database**
    ```bash
    python setup_database.py
    ```

6.  **Run the application**
    ```bash
    streamlit run streamlit_app.py
    ```

7.  **Open your browser**
    Navigate to `http://localhost:8501`

## 📋 How to Use

### 🆕 For New Students

1.  **Enter Your Information**
    - Provide your name and learning goals
    - Select your experience level (Beginner, Intermediate, Advanced)
    - Choose your preferred learning style (Visual, Auditory, Kinesthetic, Reading/Writing)

2.  **Set Your Schedule Preferences**
    - Select available days for studying
    - Choose preferred time slots (morning, afternoon, evening)
    - Set weekly time commitment (hours per week)

3.  **Generate Your Learning Path**
    - The AI will create a personalized curriculum
    - Review the generated topics and progression
    - Your learning path is automatically saved

4.  **Get Your Optimized Schedule**
    - The system creates an optimal study schedule
    - Schedule considers your availability and learning preferences
    - Topics are distributed for maximum retention

### 🔄 For Returning Students

1.  **Search for Your Profile**
    - Enter your name to find existing data
    - View your progress overview and completed topics

2.  **Dashboard Features**
    - **📚 View Learning Path**: See your complete curriculum and progress
    - **📊 View Progress**: Detailed analytics of your learning journey
    - **🤖 Adaptive Insights**: Get AI-powered recommendations
    - **📅 View Schedule**: Review your optimized study plan

### 📝 Logging Study Sessions

1.  **Access Study Session Form**
    - Click "📝 Log Study Session" from the dashboard
    - Or use the quick action buttons

2.  **Record Your Session**
    - Enter the topic you studied
    - Set duration in minutes
    - Rate your mood (1-5 scale)
    - Rate your productivity (1-5 scale)
    - Add detailed notes about what you learned

3.  **Get AI Analysis**
    - Enable "🤖 Get AI Analysis" for comprehensive feedback
    - The system analyzes effectiveness and updates progress
    - Topics are automatically marked as completed based on performance
    - Receive personalized recommendations for improvement

### 🧪 Taking Assessments

1.  **Access Assessment Form**
    - Click "🧪 Take Assessment" from the dashboard

2.  **Complete Assessment**
    - Select the topic you want to assess
    - Choose assessment type (Quiz, Project, Practice)
    - Enter your score percentage
    - Add notes about areas of strength and improvement

3.  **View Results**
    - Get immediate feedback on performance
    - See how the assessment affects your overall progress

## 🎯 Key Features in Detail

### 📈 Progress Tracking
- **Real-time Progress Updates**: See completion percentages update automatically
- **Topic Completion Logic**: Topics marked as completed based on:
  - Study session effectiveness (≥70%)
  - Assessment performance
  - Manual completion options
- **Comprehensive Analytics**: Track study hours, session count, average scores

### 🧠 AI-Powered Analysis
- **Session Effectiveness Scoring**: AI analyzes mood, productivity, and notes
- **Learning Pattern Recognition**: Identifies strengths and areas for improvement
- **Adaptive Recommendations**: Suggests schedule adjustments and focus areas
- **Topic Alignment**: Ensures study sessions align with learning path goals

### 📊 Dashboard Analytics
- **Live Progress Overview**: Real-time metrics and completion status
- **Historical Data**: Track learning journey over time
- **Performance Insights**: Identify patterns in learning effectiveness
- **Success Metrics**: Monitor goal achievement and milestone progress

### 🔧 Customization Options
- **Flexible Scheduling**: Adjust availability and time preferences
- **Learning Style Adaptation**: System adapts to your preferred learning methods
- **Difficulty Adjustment**: AI adjusts complexity based on performance
- **Goal Modification**: Update learning objectives as needed

## 🛠️ Advanced Features

### 🔍 Debug Mode
- Enable debug mode in study sessions to see:
  - AI analysis details
  - Database update processes
  - Topic matching logic
  - Progress calculation methods

### 📋 Manual Override Options
- **Manual Topic Completion**: Mark topics as completed manually if needed
- **Progress Adjustments**: Admin tools for data correction
- **Schedule Modifications**: Update preferences and regenerate schedules

### 🔄 Data Management
- **Automatic Backups**: Progress data automatically saved
- **Data Export**: Export learning data and progress reports
- **Privacy Controls**: Manage data sharing and storage preferences

## 📊 Database Schema

### Tables
- **students**: Student profiles and basic information
- **learning_paths**: Generated learning curricula
- **study_sessions**: Individual study session records
- **student_progress**: Progress tracking and completed topics
- **study_session_analyses**: AI analysis results
- **assessments**: Assessment records and scores
- **student_preferences**: Schedule and learning preferences

## 🔒 Privacy & Security

- All data stored locally in your PostgreSQL database
- OpenAI API calls are processed securely
- No personal learning data shared with third parties
- Option to delete all data at any time

## 🐛 Troubleshooting

### Common Issues

1.  **Database Connection Errors**
    - Verify PostgreSQL is running
    - Check `DATABASE_URL` in `.env` file
    - Ensure database exists and user has permissions

2.  **OpenAI API Errors**
    - Verify `OPENAI_API_KEY` is correct
    - Check API quota and billing status
    - Ensure internet connectivity

3.  **Progress Not Updating**
    - Enable debug mode to see analysis details
    - Check topic name matching with learning path
    - Verify effectiveness scores (need ≥70% for auto-completion)

4.  **Missing Features**
    - Refresh the page and clear browser cache
    - Check console for JavaScript errors
    - Restart Streamlit application

### Debug Tools

- **🔍 Debug Data**: View raw progress and system data
- **Show Learning Path Topics**: See exact topic names for matching
- **Session Analysis Debug**: Step-by-step analysis breakdown
- **Database Verification**: Check what's actually saved

## 🚀 Future Enhancements

- **Mobile App**: React Native mobile application
- **Collaborative Learning**: Study groups and peer interaction
- **Advanced Analytics**: Machine learning insights and predictions
- **Integration APIs**: Connect with external learning platforms
- **Gamification**: Achievements, streaks, and learning rewards

## 🤝 Contributing

1.  Fork the repository
2.  Create a feature branch
3.  Make your changes
4.  Add tests if applicable
5.  Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 📞 Support

For issues or questions:
- Check the troubleshooting section above
- Enable debug mode for detailed error information
- Review console logs for technical details

---

**Happy Learning! 🎓✨**

*Transform your learning journey with AI-powered personalization and adaptive insights.*