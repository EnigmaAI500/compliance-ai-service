# Deployment Checklist

## Pre-Deployment

### Azure OpenAI Setup
- [ ] Created Azure OpenAI resource in Azure Portal
- [ ] Deployed GPT-4 or GPT-4o model (NOT GPT-3.5)
- [ ] Noted down endpoint URL
- [ ] Noted down API key
- [ ] Noted down deployment name
- [ ] Tested connection from Azure Portal

### Environment Configuration
- [ ] Copied `.env.example` to `.env`
- [ ] Set `AZURE_OPENAI_ENDPOINT`
- [ ] Set `AZURE_OPENAI_API_KEY`
- [ ] Set `AZURE_OPENAI_DEPLOYMENT_RISK`
- [ ] Verified no `.env` file committed to git

### Code Review
- [ ] Reviewed `bulk_risk_engine.py` risk scoring rules
- [ ] Customized high-risk occupation categories for your region
- [ ] Updated FATF country lists if needed
- [ ] Reviewed sanctions matching logic
- [ ] Checked email domain risk list

## Testing

### Local Testing
- [ ] Built Docker image: `docker compose build`
- [ ] Started services: `docker compose up`
- [ ] Service accessible at http://localhost:8000
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] Checked logs: `docker compose logs ai-service`

### Functionality Testing
- [ ] Tested with LOW risk customer (UZ citizen, retail banking)
- [ ] Tested with HIGH risk customer (IRN citizen, money service business)
- [ ] Tested with CRITICAL risk customer (PRK citizen, front company)
- [ ] Verified VPN detection works
- [ ] Verified device reuse detection works
- [ ] Verified email domain risk works
- [ ] Tested with invalid Excel file (proper error message)
- [ ] Tested with missing required columns (proper error message)

### Response Validation
- [ ] Response has `report_id`
- [ ] Response has `file` with validation status
- [ ] Response has `summary` with risk distribution
- [ ] Response has `customers` array
- [ ] Each customer has `risk` object with all required fields
- [ ] Each customer has `tags` array with proper evidence dicts
- [ ] Each customer has `recommendedActions` array with proper objects
- [ ] No Pydantic validation errors

### Performance Testing
- [ ] Tested with 10 customers (should complete in <1 minute)
- [ ] Tested with 50 customers (should complete in <5 minutes)
- [ ] Tested with 100 customers (should complete in <10 minutes)
- [ ] Monitored Azure OpenAI usage and costs
- [ ] Checked for rate limiting issues

## Security

### Credentials
- [ ] API keys stored in environment variables only
- [ ] No hardcoded credentials in code
- [ ] `.env` file in `.gitignore`
- [ ] Secrets management system in place (Azure Key Vault, etc.)

### Data Privacy
- [ ] Reviewed data sent to Azure OpenAI
- [ ] Ensured compliance with GDPR/data protection laws
- [ ] Customer consent for data processing obtained
- [ ] Data retention policy documented
- [ ] Audit logging configured

### Network Security
- [ ] Service runs behind firewall/VPN
- [ ] API endpoint uses HTTPS in production
- [ ] Rate limiting configured
- [ ] Input validation in place
- [ ] Error messages don't leak sensitive info

## Production Deployment

### Infrastructure
- [ ] Docker host/Kubernetes cluster provisioned
- [ ] Sufficient resources (4GB RAM minimum)
- [ ] Load balancer configured (if multiple instances)
- [ ] Backup and disaster recovery plan
- [ ] Monitoring and alerting set up

### Database (if used)
- [ ] PostgreSQL installed and configured
- [ ] Database migrations applied
- [ ] Backup schedule configured
- [ ] Connection pooling configured

### Monitoring
- [ ] Application logs centralized
- [ ] Azure OpenAI usage monitored
- [ ] Error rate alerts configured
- [ ] Performance metrics tracked
- [ ] Uptime monitoring configured

### Documentation
- [ ] API documentation published
- [ ] Excel template shared with users
- [ ] QUICKSTART.md guide shared
- [ ] IMPLEMENTATION_GUIDE.md available for developers
- [ ] EXCEL_TEMPLATE_SPEC.md shared with data entry team
- [ ] Support contact information documented

## Post-Deployment

### Verification
- [ ] Smoke test with real production data
- [ ] Verify all integrations working
- [ ] Check Azure OpenAI costs
- [ ] Review initial error logs
- [ ] Verify performance metrics

### User Training
- [ ] Training session for compliance officers
- [ ] Demo of risk scoring system
- [ ] Excel template walkthrough
- [ ] How to interpret results
- [ ] Escalation procedures

### Continuous Improvement
- [ ] Feedback collection process established
- [ ] Regular review of risk rules scheduled
- [ ] FATF list update schedule defined
- [ ] Sanctions database update schedule defined
- [ ] Performance optimization plan

## Rollback Plan

If issues occur:

1. **Stop the service**
   ```bash
   docker compose down
   ```

2. **Review logs**
   ```bash
   docker compose logs ai-service > error-logs.txt
   ```

3. **Restore previous version**
   ```bash
   git checkout <previous-commit>
   docker compose up --build
   ```

4. **Contact support** with error logs

## Success Criteria

Service is ready for production when:
- [ ] All checklist items completed
- [ ] Successfully processed 100+ test customers
- [ ] Zero Pydantic validation errors
- [ ] Response time < 5 seconds per customer
- [ ] Azure OpenAI costs within budget
- [ ] Security review passed
- [ ] Stakeholder approval obtained

## Emergency Contacts

- **Azure Support**: https://portal.azure.com (Support ticket)
- **Technical Lead**: [Your contact info]
- **Compliance Officer**: [Contact info]
- **DevOps Team**: [Contact info]

## Notes

Date Deployed: __________
Deployed By: __________
Version: v2.0.0
Azure OpenAI Model: __________

Special Notes:
_________________________________
_________________________________
_________________________________
