import React from 'react';
import { Result, Button, Typography } from 'antd';

const { Paragraph, Text } = Typography;

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Something went wrong"
          subTitle="Sorry, an unexpected error occurred in this component."
          extra={[
            <Button type="primary" key="reload" onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          ]}
        >
          <div className="desc">
            <Paragraph>
              <Text
                strong
                style={{
                  fontSize: 16,
                }}
              >
                The content you requested has the following error:
              </Text>
            </Paragraph>
            <Paragraph>
              <Text type="danger">{this.state.error && this.state.error.toString()}</Text>
            </Paragraph>
            {import.meta.env.DEV && (
              <details style={{ whiteSpace: 'pre-wrap' }}>
                {this.state.errorInfo && this.state.errorInfo.componentStack}
              </details>
            )}
          </div>
        </Result>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
