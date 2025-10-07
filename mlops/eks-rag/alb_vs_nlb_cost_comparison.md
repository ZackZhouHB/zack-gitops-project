# AWS Elastic Load Balancing Cost Analysis Estimate Report

## Service Overview

AWS Elastic Load Balancing is a fully managed, serverless service that allows you to This project uses multiple AWS services.. This service follows a pay-as-you-go pricing model, making it cost-effective for various workloads.

## Pricing Model

This cost analysis estimate is based on the following pricing model:
- **ON DEMAND** pricing (pay-as-you-go) unless otherwise specified
- Standard service configurations without reserved capacity or savings plans
- No caching or optimization techniques applied

## Assumptions

- Standard ON DEMAND pricing model
- 2 load balancers running 24/7 (730 hours/month)
- Typical EKS workload with moderate traffic
- LCU usage based on standard web application patterns

## Limitations and Exclusions

- Data transfer costs
- Cross-zone load balancing charges
- SSL certificate costs
- Target health check costs beyond included limits

## Cost Breakdown

### Unit Pricing Details

| Service | Resource Type | Unit | Price | Free Tier |
|---------|--------------|------|-------|------------|
| 2x Application Load Balancers (ALB) | Hourly Charge | ALB-hour | $0.0252 | None |
| 2x Application Load Balancers (ALB) | Lcu Charge | LCU-hour | $0.008 | None |
| 2x Network Load Balancers (NLB) | Hourly Charge | NLB-hour | $0.0252 | None |
| 2x Network Load Balancers (NLB) | Lcu Charge | LCU-hour | $0.006 | None |

### Cost Calculation

| Service | Usage | Calculation | Monthly Cost |
|---------|-------|-------------|-------------|
| 2x Application Load Balancers (ALB) | 2 ALBs running 24/7 with moderate traffic (estimated 1 LCU average) (Alb Hours: 2 ALBs × 730 hours = 1,460 ALB-hours, Lcu Hours: 2 ALBs × 1 LCU × 730 hours = 1,460 LCU-hours) | ($0.0252 × 1,460 ALB-hours) + ($0.008 × 1,460 LCU-hours) = $36.79 + $11.68 = $48.47 | $37.58 |
| 2x Network Load Balancers (NLB) | 2 NLBs running 24/7 with moderate traffic (estimated 1 LCU average) (Nlb Hours: 2 NLBs × 730 hours = 1,460 NLB-hours, Lcu Hours: 2 NLBs × 1 LCU × 730 hours = 1,460 LCU-hours) | ($0.0252 × 1,460 NLB-hours) + ($0.006 × 1,460 LCU-hours) = $36.79 + $8.76 = $45.55 | $45.51 |
| **Total** | **All services** | **Sum of all calculations** | **$83.09/month** |

### Free Tier

AWS offers a Free Tier for many services. Check the AWS Free Tier page for current offers and limitations.

## Cost Scaling with Usage

The following table illustrates how cost estimates scale with different usage levels:

| Service | Low Usage | Medium Usage | High Usage |
|---------|-----------|--------------|------------|
| 2x Application Load Balancers (ALB) | $18/month | $37/month | $75/month |
| 2x Network Load Balancers (NLB) | $22/month | $45/month | $91/month |

### Key Cost Factors

- **2x Application Load Balancers (ALB)**: 2 ALBs running 24/7 with moderate traffic (estimated 1 LCU average)
- **2x Network Load Balancers (NLB)**: 2 NLBs running 24/7 with moderate traffic (estimated 1 LCU average)

## Projected Costs Over Time

The following projections show estimated monthly costs over a 12-month period based on different growth patterns:

Base monthly cost calculation:

| Service | Monthly Cost |
|---------|-------------|
| 2x Application Load Balancers (ALB) | $37.58 |
| 2x Network Load Balancers (NLB) | $45.51 |
| **Total Monthly Cost** | **$83** |

| Growth Pattern | Month 1 | Month 3 | Month 6 | Month 12 |
|---------------|---------|---------|---------|----------|
| Steady | $83/mo | $83/mo | $83/mo | $83/mo |
| Moderate | $83/mo | $91/mo | $106/mo | $142/mo |
| Rapid | $83/mo | $100/mo | $133/mo | $237/mo |

* Steady: No monthly growth (1.0x)
* Moderate: 5% monthly growth (1.05x)
* Rapid: 10% monthly growth (1.1x)

## Detailed Cost Analysis

### Pricing Model

ON DEMAND


### Exclusions

- Data transfer costs
- Cross-zone load balancing charges
- SSL certificate costs
- Target health check costs beyond included limits

### Recommendations

#### Immediate Actions

- NLBs are $2.92/month cheaper than ALBs for your 2-load balancer setup
- Consider your routing requirements - ALBs provide path-based routing, NLBs provide better performance
- Monitor actual LCU consumption as it varies significantly based on traffic patterns
#### Best Practices

- Use ALBs if you need Layer 7 features (path-based routing, host-based routing, SSL termination)
- Use NLBs for Layer 4 load balancing with ultra-low latency requirements
- Consider consolidating to 1 ALB with path-based routing if technically feasible
- Monitor CloudWatch metrics to optimize LCU usage and right-size your load balancers



## Cost Optimization Recommendations

### Immediate Actions

- NLBs are $2.92/month cheaper than ALBs for your 2-load balancer setup
- Consider your routing requirements - ALBs provide path-based routing, NLBs provide better performance
- Monitor actual LCU consumption as it varies significantly based on traffic patterns

### Best Practices

- Use ALBs if you need Layer 7 features (path-based routing, host-based routing, SSL termination)
- Use NLBs for Layer 4 load balancing with ultra-low latency requirements
- Consider consolidating to 1 ALB with path-based routing if technically feasible

## Conclusion

By following the recommendations in this report, you can optimize your AWS Elastic Load Balancing costs while maintaining performance and reliability. Regular monitoring and adjustment of your usage patterns will help ensure cost efficiency as your workload evolves.
