# Roadmap - DNS Web Manager

> **Updated:** 2025-12
> **Current Version:** 2.0.0

## Current Version - Features

### Implemented
- [x] Native installation (Master/Slave) via shell scripts
- [x] Complete CRUD for zones and DNS records
- [x] JWT authentication
- [x] 2FA/TOTP (Google Authenticator)
- [x] Permission system (Admin/Operator/Viewer)
- [x] User management
- [x] Zone backup and restore
- [x] Action auditing
- [x] Dashboard with statistics
- [x] API rate limiting
- [x] Dark/Light Mode
- [x] SSO/Keycloak integration

### In Progress
- [ ] Slave management interface improvements
- [ ] Health monitoring dashboard

---

## Upcoming Versions

### v2.1.0 - Slave Management
| Feature | Description | Priority |
|---------|-------------|----------|
| Slaves Interface | Frontend screen to manage slaves | High |
| Health Check | Real-time slave status | High |
| Zone Transfer Status | Monitor AXFR/IXFR | Medium |

### v2.2.0 - Security
| Feature | Description | Priority |
|---------|-------------|----------|
| HTTPS/TLS | Let's Encrypt or custom certificate | High |
| DNS Validation | named-checkzone before saving | Medium |
| API Keys | Key authentication for automation | Medium |

### v2.3.0 - Operations
| Feature | Description | Priority |
|---------|-------------|----------|
| Import/Export | Zone file upload, BIND export | Medium |
| Advanced Logs | Filters, CSV/JSON export | Medium |
| Notifications | Email alerts on failures | Low |

---

## Backlog (Future)

### Enterprise Integration
| Feature | Description |
|---------|-------------|
| LDAP/SSO | Active Directory integration |
| SAML/OIDC | Single Sign-On |
| Multi-tenancy | Organizations, tenant isolation |

### Automation
| Feature | Description |
|---------|-------------|
| Webhooks | Notify external systems |
| Terraform Provider | Manage DNS via IaC |
| Ansible Role | Installation automation |

### Monitoring
| Feature | Description |
|---------|-------------|
| Prometheus Metrics | Export metrics |
| Health Dashboard | Detailed status of all components |
| Alerting | PagerDuty/Slack integration |

---

## Version History

### v2.0.0 (2025-12)
- Complete refactoring: Docker → Native installation
- SQLite as database (zero config)
- Shell installation scripts
- 2FA/TOTP implemented
- Rate limiting
- SSO/Keycloak support

### v1.0.0 (2025-11)
- Initial version with Docker
- PostgreSQL as database
- docker-compose for orchestration
- Helm charts for Kubernetes

---

## Notes

- Priorities may change based on feedback
- Estimates not included (depends on availability)
- Suggestions welcome via Issues in the repository
