import {describe,it,expect} from 'vitest';
import {reviewQueue,queueStep} from './library';

const tracks=[{id:'a',review_state:'reviewed'},{id:'b',review_state:'unreviewed'},{id:'c',review_state:'stale'},{id:'d',review_state:'unreviewed'}];
const priority={b:{score:1},c:{score:5},d:{score:1}};

describe('review queue navigation',()=>{
 it('orders unreviewed tracks by priority, ties in library order',()=>{
  expect(reviewQueue(tracks,priority)).toEqual(['c','b','d']);
 });
 it('continues from where a just-finished track was',()=>{
  const before=['c','a','b','d'];
  expect(queueStep(['c','b','d'],'a',1,before)).toBe('b');
  expect(queueStep(['c','b','d'],'a',-1,before)).toBe('c');
  expect(queueStep(['c','b','d'],'x',1,before)).toBe('c');
 });
 it('steps forward and back, and stops at the ends',()=>{
  const q=['c','b','d'];
  expect(queueStep(q,'b',1)).toBe('d');
  expect(queueStep(q,'b',-1)).toBe('c');
  expect(queueStep(q,'d',1)).toBeNull();
  expect(queueStep(q,'c',-1)).toBeNull();
 });
 it('starts at the top of the queue from a track outside it',()=>{
  expect(queueStep(['c','b'],'a',1)).toBe('c');
  expect(queueStep(['c','b'],null,-1)).toBeNull();
 });
});
