#include "word0196_equivalent.h"

#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Strict host-only text transport. No JSON library, ROM input, scheduler or ECU. */
static void print_state(const word0196_state *state)
{
    size_t i;
    printf("{\"a\":%u,\"psw\":%u,\"pc\":%u,\"lrb\":%u,"
           "\"x1\":%u,\"x2\":%u,\"dp\":%u,\"usp\":%u,\"ssp\":%u,"
           "\"sf\":%s,\"halted\":%s,\"registers\":[",
           (unsigned)state->a, (unsigned)state->psw, (unsigned)state->pc,
           (unsigned)state->lrb, (unsigned)state->x1, (unsigned)state->x2,
           (unsigned)state->dp, (unsigned)state->usp, (unsigned)state->ssp,
           state->sf ? "true" : "false", state->halted ? "true" : "false");
    for (i = 0; i < 8; ++i) {
        printf("%s%u", i == 0 ? "" : ",", (unsigned)state->local[i]);
    }
    printf("],\"ram0117\":%u,\"ram0124\":%u,\"ram0128\":%u,\"ram012A\":%u,"
           "\"ram018E\":%u,\"ram018F\":%u,\"ram0196Lo\":%u,\"ram0196Hi\":%u}",
           (unsigned)state->ram0117, (unsigned)state->ram0124,
           (unsigned)state->ram0128, (unsigned)state->ram012a,
           (unsigned)state->ram018e, (unsigned)state->ram018f,
           (unsigned)state->ram0196[0], (unsigned)state->ram0196[1]);
}

static void print_result(const char *id, const word0196_result *result)
{
    size_t i;
    printf("{\"id\":\"%s\",\"status\":\"Complete\",\"entry\":", id);
    print_state(&result->entry);
    printf(",\"final\":");
    print_state(&result->final);
    printf(",\"compare\":{\"left\":%u,\"right\":%u,\"cf\":%s,\"zf\":%s},"
           "\"branchTaken\":%s,\"stopPc\":%u,\"steps\":[",
           (unsigned)result->compare_left, (unsigned)result->compare_right,
           result->compare_cf ? "true" : "false", result->compare_zf ? "true" : "false",
           result->branch_taken ? "true" : "false", (unsigned)result->final.pc);
    for (i = 0; i < result->step_count; ++i) {
        const word0196_step *step = &result->steps[i];
        printf("%s{\"pc\":%u,\"nextPc\":%u,\"a\":%u,\"psw\":%u}",
               i == 0 ? "" : ",", (unsigned)step->pc, (unsigned)step->next_pc,
               (unsigned)step->a, (unsigned)step->psw);
    }
    printf("],\"accesses\":[");
    for (i = 0; i < result->access_count; ++i) {
        const word0196_access *access = &result->accesses[i];
        printf("%s{\"pc\":%u,\"address\":%u,\"width\":%u,\"write\":%s,\"value\":%u}",
               i == 0 ? "" : ",", (unsigned)access->pc, (unsigned)access->address,
               (unsigned)access->width_bits, access->write ? "true" : "false",
               (unsigned)access->value);
    }
    printf("],\"writes\":[");
    for (i = 0; i < result->write_count; ++i) {
        const word0196_write *write = &result->writes[i];
        printf("%s{\"pc\":%u,\"address\":%u,\"width\":%u,\"oldValue\":%u,"
               "\"newValue\":%u,\"eventIndex\":%" PRIu32 ",\"writeOrdinal\":%" PRIu32 "}",
               i == 0 ? "" : ",", (unsigned)write->pc, (unsigned)write->address,
               (unsigned)write->width_bits, (unsigned)write->old_value,
               (unsigned)write->new_value, write->event_index, write->write_ordinal);
    }
    printf("]}\n");
}

static bool parse_line(char *line, char **id, uint32_t fields[29])
{
    char *cursor = line;
    size_t count = 0;
    while (isspace((unsigned char)*cursor)) { ++cursor; }
    *id = cursor;
    while (*cursor != '\0' && !isspace((unsigned char)*cursor)) {
        if (!isalnum((unsigned char)*cursor) && *cursor != '_' && *cursor != '-') {
            return false;
        }
        ++cursor;
    }
    if (cursor == *id || *cursor == '\0') { return false; }
    *cursor++ = '\0';
    while (count < 29) {
        char *end;
        unsigned long value;
        while (isspace((unsigned char)*cursor)) { ++cursor; }
        if (!isdigit((unsigned char)*cursor)) { return false; }
        errno = 0;
        value = strtoul(cursor, &end, 10);
        if (errno != 0 || end == cursor || value > UINT32_MAX ||
            (*end != '\0' && !isspace((unsigned char)*end))) { return false; }
        fields[count++] = (uint32_t)value;
        cursor = end;
    }
    while (isspace((unsigned char)*cursor)) { ++cursor; }
    if (*cursor != '\0') { return false; }
    for (count = 0; count < 9; ++count) {
        if (fields[count] > UINT16_MAX) { return false; }
    }
    if (fields[9] > 1 || fields[10] > 1) { return false; }
    for (count = 13; count < 29; ++count) {
        if (fields[count] > UINT8_MAX) { return false; }
    }
    return true;
}

int main(void)
{
    char line[1024];
    uint32_t fields[29];
    size_t i, count = 0;
    while (fgets(line, sizeof(line), stdin) != NULL) {
        char *id;
        word0196_state state = {0};
        word0196_replay_context context;
        word0196_result result;
        word0196_status status;
        if (strchr(line, '\n') == NULL && !feof(stdin)) {
            fprintf(stderr, "Input line too long at row %zu\n", count + 1);
            return 2;
        }
        if (!parse_line(line, &id, fields)) {
            fprintf(stderr, "Invalid closed replay input at row %zu\n", count + 1);
            return 2;
        }
        state.a = (uint16_t)fields[0]; state.psw = (uint16_t)fields[1];
        state.pc = (uint16_t)fields[2]; state.lrb = (uint16_t)fields[3];
        state.x1 = (uint16_t)fields[4]; state.x2 = (uint16_t)fields[5];
        state.dp = (uint16_t)fields[6]; state.usp = (uint16_t)fields[7];
        state.ssp = (uint16_t)fields[8]; state.sf = fields[9] != 0;
        state.halted = fields[10] != 0;
        context.write_ordinal_base = fields[11]; context.event_index = fields[12];
        for (i = 0; i < 8; ++i) { state.local[i] = (uint8_t)fields[13 + i]; }
        state.ram0117 = (uint8_t)fields[21]; state.ram0124 = (uint8_t)fields[22];
        state.ram0128 = (uint8_t)fields[23]; state.ram012a = (uint8_t)fields[24];
        state.ram018e = (uint8_t)fields[25]; state.ram018f = (uint8_t)fields[26];
        state.ram0196[0] = (uint8_t)fields[27]; state.ram0196[1] = (uint8_t)fields[28];
        status = word0196_replay(&state, &context, &result);
        if (status != WORD0196_OK) {
            fprintf(stderr, "Replay refused row %zu, status %u\n", count + 1, (unsigned)status);
            return 3;
        }
        print_result(id, &result);
        ++count;
    }
    if (ferror(stdin)) { return 2; }
    return 0;
}
