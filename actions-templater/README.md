actions-templater

To build and push Docker images for both AMD64 and ARM64, add this to the
repository's `.github/actions.json`:

```json
{
  "arm_enable": true
}
```

When the setting is absent or `false`, the Docker workflow uses its existing
single-platform build.
