<?php

/*
 * WARNING
 *
 * This file gets modified by automatic processes and all lines that are not
 * active code (ie. comments) are lost during that process.
 *
 * If you want to document things with comments or use constants add your settings
 * in a '<NAME>.config.php' file which will be included and rendered into this file.
 *
 * Example:
 *   <?php
 *   $CONFIG = [];
 *
 * See also: https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#multiple-merged-configuration-files
 */
$CONFIG = array (
  'htaccess.RewriteBase' => '/',
  'memcache.local' => '\\OC\\Memcache\\APCu',
  'apps_paths' => 
  array (
    0 => 
    array (
      'path' => '/var/www/html/apps',
      'url' => '/apps',
      'writable' => false,
    ),
    1 => 
    array (
      'path' => '/var/www/html/custom_apps',
      'url' => '/custom_apps',
      'writable' => true,
    ),
  ),
  'memcache.distributed' => '\\OC\\Memcache\\Redis',
  'memcache.locking' => '\\OC\\Memcache\\Redis',
  'redis' => 
  array (
    'host' => 'redis',
    'password' => '',
    'port' => 6379,
  ),
  'overwriteprotocol' => '',
  'overwrite.cli.url' => 'https://tdemers.duckdns.org',
  'trusted_proxies' => 
  array (
    0 => '127.0.0.1',
  ),
  'upgrade.disable-web' => true,
  'passwordsalt' => 's829XcyIDOhs5ttNJ8ylrI8jE1ZQ+N',
  'secret' => 'K9kh9FOiBVWx/TgZfctm1CKXAZldtF5rX6qu11Df+g6B77F3',
  'trusted_domains' => 
  array (
    0 => 'localhost',
    1 => 'tdemers.duckdns.org',
    2 => '192.168.0.31',
    3 => 'nextcloud.tdemers.duckdns.org',
  ),
  'datadirectory' => '/var/www/html/data',
  'dbtype' => 'pgsql',
  'version' => '34.0.2.1',
  'instanceid' => 'ocx2deskhnnh',
  'dbname' => 'nextcloud',
  'dbhost' => 'db',
  'dbtableprefix' => 'oc_',
  'dbuser' => 'oc_admin',
  'dbpassword' => 'ba7oC(SE&fq(z&K<n!mjkEU0R[+]0|',
  'installed' => true,
  'maintenance' => false,
  'overwritewebroot' => '',
);
