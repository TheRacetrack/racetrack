FROM {{ base_image }}
ENV FATMAN_NAME "{{ manifest.name }}"
ENV FATMAN_ENTRYPOINT_HOSTNAME "{{ resource_name }}-user-module"
ENV FATMAN_VERSION "{{ manifest.version }}"
ENV GIT_VERSION "{{ git_version }}"
ENV DEPLOYED_BY_RACETRACK_VERSION "{{ deployed_by_racetrack_version }}"
