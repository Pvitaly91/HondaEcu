using System.Runtime.CompilerServices;

// Tests exercise the same fixed synthetic-only composition path. This does not
// expose an arbitrary-ROM authority factory in the public application API.
[assembly: InternalsVisibleTo("HondaEcu.Core.Tests")]
