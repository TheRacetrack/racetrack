# Glossary

Workloads:

- **Deployment** - a request by user to run Image on cluster (Image becoming a Fatman)  
- **Fatman Manifest** - a YAML file in the root of your Job, which specifies the job type
  and provides configuration values for your Job
- **Fatman** - The source code converted to REST microservice workload with a standardized interface, served on Racetrack.
- **Fatman Image** - Job built into Docker image
- **Job Type** - one of the languages and frameworks supported by Racetrack that user choose to develop a job in
- **Job** - A blueprint for creating Fatman, 
  consisting of source code (written in the style required by Racetrack) and Fatman Manifest file.
- **ML Model** - An application using Machine Learning algorithms created by Data Scentists or
  Developers, transforming input data & parameters into results.

Platform:

- **ESC (External Service Consumer)** - A system external to the Racetrack using its services.
- **Fatman Webview** - User-defined web endpoint for human use served by Fatman
- **Language Wrapper** - A wrapper for a specific programming language, which is used to convert source code into a Fatman Image.
- **Lifecycle** - Lifecycle is a subcomponent of Racetrack
  responsible for automated and simplified PUC deployment and monitoring condition of deployed workloads.
- **PUB** - Subcomponent of Racetrack taking care of public access, security & routing, handling requests
  from External Consumers.
- **PUC (Platform Utility Component)** - Any business workload running on the platform. 
  In particular, it might be a Machine Learning Model or any other service.
- **RBAC** - Role-based access control. A system selectively restricting access to some group of users.
- **Racetrack admin panel** - A panel for managing database models,
  hosted by Lifecycle component, eg. at `https://racetrack.<cluster_dns>/lifecycle/admin`
- **Racetrack Dashboard** - Web page showing current state of Racetrack and summary of deployed fatmen in a cluster.
