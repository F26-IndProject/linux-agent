/*
 * spawn.c — Launch a process with systemd as parent (Linux equivalent of spawn.exe)
 *
 * Usage: ./spawn <command> [args...]
 * Example: ./spawn firefox https://google.com
 *
 * Technique: double-fork daemon pattern
 *   1. spawn forks → child; spawn exits immediately (python3 is no longer involved)
 *   2. child calls setsid() → new session leader
 *   3. child forks → grandchild; child exits
 *   4. grandchild is orphaned → reparented to systemd --user
 *   5. grandchild execs the target command
 *   6. spawn writes grandchild PID to stdout before exiting so caller can track it
 *
 * Compile: gcc -o spawn spawn.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <command> [args...]\n", argv[0]);
        return 1;
    }

    /* Pipe to send grandchild PID back to parent (python3) */
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        perror("pipe");
        return 1;
    }

    pid_t child = fork();
    if (child < 0) {
        perror("fork");
        return 1;
    }

    if (child > 0) {
        /* ── Parent (spawn) ─────────────────────────────────────────
         * Read grandchild PID from pipe, print it, then exit.
         * Python3 reads this PID to track the process for killing later.
         */
        close(pipefd[1]);
        pid_t grandchild_pid = 0;
        read(pipefd[0], &grandchild_pid, sizeof(pid_t));
        close(pipefd[0]);
        waitpid(child, NULL, 0);  /* reap child so it doesn't become zombie */
        printf("%d\n", grandchild_pid);
        fflush(stdout);
        return 0;
    }

    /* ── First child ────────────────────────────────────────────────
     * Detach from session, fork again, then exit.
     */
    close(pipefd[0]);
    setsid();  /* new session — detach from agent's process group */

    pid_t grandchild = fork();
    if (grandchild < 0) {
        close(pipefd[1]);
        _exit(1);
    }

    if (grandchild > 0) {
        /* Send grandchild PID to parent, then exit */
        write(pipefd[1], &grandchild, sizeof(pid_t));
        close(pipefd[1]);
        _exit(0);  /* child exits → grandchild orphaned → reparented to systemd */
    }

    /* ── Grandchild (the actual process) ────────────────────────────
     * Redirect stdio to /dev/null and exec the target command.
     * At this point our parent (child) has exited, so our PPID
     * becomes systemd --user.
     */
    close(pipefd[1]);

    int devnull = open("/dev/null", O_RDWR);
    if (devnull >= 0) {
        dup2(devnull, STDIN_FILENO);
        dup2(devnull, STDOUT_FILENO);
        dup2(devnull, STDERR_FILENO);
        close(devnull);
    }

    execvp(argv[1], &argv[1]);

    /* exec failed */
    _exit(1);
}
