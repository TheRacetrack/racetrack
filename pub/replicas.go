package main

import (
	"fmt"
	"net"
	"slices"
	"time"

	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

type replicaDiscovery struct {
	ReplicaDiscoveryHostname string
	ShouldExit               bool
	MyAddr                   string
	otherReplicaAddrs        []string
	listenPort               string
}

func NewReplicaDiscovery(cfg *Config) *replicaDiscovery {
	discovery := &replicaDiscovery{
		ReplicaDiscoveryHostname: cfg.ReplicaDiscoveryHostname,
		ShouldExit:               false,
		otherReplicaAddrs:        []string{},
		listenPort:               cfg.ListenPort,
	}
	if cfg.ReplicaDiscoveryHostname != "" {
		go func() {
			time.Sleep(1 * time.Second)
			for !discovery.ShouldExit {
				err := discovery.refreshAddrs()
				if err != nil {
					log.Error("Failed to get replica IPs", log.Ctx{"error": err})
				}
				time.Sleep(30 * time.Second)
			}
		}()
	}
	return discovery
}

func NewStaticReplicaDiscovery(addrs []string, myAddr string) *replicaDiscovery {
	return &replicaDiscovery{
		otherReplicaAddrs: addrs,
		MyAddr:            myAddr,
	}
}

func (s *replicaDiscovery) refreshAddrs() error {
	allIps, err := s.getAllReplicaIPs()
	if err != nil {
		return errors.Wrap(err, "getting Pub replica IPs")
	}
	myIps, err := getMyLocalIPs()
	if err != nil {
		return errors.Wrap(err, "reading local IP addresses")
	}
	otherReplicaIPs, err := s.getOtherReplicaIPs(allIps, myIps)
	if err != nil {
		return err
	}
	s.otherReplicaAddrs = MapSlice(otherReplicaIPs, func(ip string) string {
		return fmt.Sprintf("%s:%v", ip, s.listenPort)
	})
	myReplicaIP, err := s.getMyReplicaIP(allIps, myIps)
	if err != nil {
		return err
	}
	myNewAddr := fmt.Sprintf("%s:%v", myReplicaIP, s.listenPort)
	if s.MyAddr != myNewAddr {
		s.MyAddr = myNewAddr
		log.Info("Assigned Pub instance Address", log.Ctx{
			"myAddr": myNewAddr,
		})
	}
	return nil
}

func (s *replicaDiscovery) getOtherReplicaIPs(allIps []string, myIps []string) ([]string, error) {
	otherIps := []string{}
	for _, ip := range allIps {
		if !slices.Contains(myIps, ip) {
			otherIps = append(otherIps, ip)
		}
	}
	return otherIps, nil
}

func (s *replicaDiscovery) getMyReplicaIP(allIps []string, myIps []string) (string, error) {
	for _, ip := range allIps {
		if slices.Contains(myIps, ip) {
			return ip, nil
		}
	}
	return "", errors.New("Failed to find my replica IP")
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
			continue
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
