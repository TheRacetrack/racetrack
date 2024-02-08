package main

import (
	"net"
	"slices"
	"time"

	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

type replicaDiscovery struct {
	ReplicaDiscoveryHostname string
	ShouldExit               bool
	otherReplicaIPs          []string
}

func NewReplicaDiscovery(cfg *Config) *replicaDiscovery {
	discovery := &replicaDiscovery{
		ReplicaDiscoveryHostname: cfg.ReplicaDiscoveryHostname,
		ShouldExit:               false,
		otherReplicaIPs:          []string{},
	}
	if cfg.ReplicaDiscoveryHostname != "" {
		go func() {
			for !discovery.ShouldExit {
				err := discovery.refreshIPs()
				if err != nil {
					log.Error("Failed to get replica IPs", log.Ctx{"error": err})
				}
				time.Sleep(30 * time.Second)
			}
		}()
	}
	return discovery
}

func (s *replicaDiscovery) refreshIPs() error {
	otherReplicaIPs, err := s.getOtherReplicaIPs()
	if err != nil {
		return err
	}
	s.otherReplicaIPs = otherReplicaIPs
	return nil
}

func (s *replicaDiscovery) getOtherReplicaIPs() ([]string, error) {
	allIps, err := s.getAllReplicaIPs()
	if err != nil {
		return nil, errors.Wrap(err, "getting Pub replica IPs")
	}
	myIps, err := getMyLocalIPs()
	if err != nil {
		return nil, errors.Wrap(err, "reading local IP addresses")
	}
	otherIps := []string{}
	for _, ip := range allIps {
		if !slices.Contains(myIps, ip) {
			otherIps = append(otherIps, ip)
		}
	}
	return otherIps, nil
}

func getMyLocalIPs() ([]string, error) {
	ips := []string{}
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, errors.Wrap(err, "Failed to get network interfaces")
	}
	for _, i := range ifaces {
		addrs, err := i.Addrs()
		if err != nil {
			log.Error("Failed to get addresses for network interface", log.Ctx{
				"interface": i.Name,
				"error":     err,
			})
		}
		for _, addr := range addrs {
			switch v := addr.(type) {
			case *net.IPNet:
				ip := v.IP.String()
				ips = append(ips, ip)
			case *net.IPAddr:
				ip := v.IP.String()
				ips = append(ips, ip)
			}
		}
	}
	return ips, nil
}

func (s *replicaDiscovery) getAllReplicaIPs() ([]string, error) {
	hostname := s.ReplicaDiscoveryHostname
	if hostname == "" {
		return []string{}, nil
	}
	addrs, err := net.LookupHost(hostname)
	if err != nil {
		return nil, errors.Wrap(err, "Failed to resolve DNS name")
	}
	return addrs, nil
}
